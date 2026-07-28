import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from excess_return_engine.model import (
    ForecastComputation,
    ForecastRequest,
    forecast_configuration_id,
    generate_forecast,
)
from excess_return_engine.runs import (
    RUN_ARTIFACT_VERSION,
    execute_forecast,
)
from tests.test_excess_return_model import synthetic_panels


def request() -> ForecastRequest:
    return ForecastRequest(
        permno=3,
        selected_factors=("size",),
        tuning_months=6,
        calibration_months=12,
        minimum_training_months=48,
        alpha_grid=(0.0001,),
        l1_ratio_grid=(0.5,),
    )


class ForecastRunTests(unittest.TestCase):
    def test_preflight_id_matches_fitted_result_and_tracks_content(self) -> None:
        training, inference = synthetic_panels()
        initial = forecast_configuration_id(training, inference, request())
        modified = training.copy()
        modified.loc[0, "excess_return_next_month"] += 0.01

        changed = forecast_configuration_id(modified, inference, request())

        self.assertNotEqual(initial, changed)

    def test_factor_subsets_share_scope_data_version(self) -> None:
        training, inference = synthetic_panels()
        size_result = generate_forecast(training, inference, request())
        momentum_result = generate_forecast(
            training,
            inference,
            replace(request(), selected_factors=("momentum_12_1",)),
        )

        self.assertEqual(size_result.data_version, momentum_result.data_version)
        self.assertNotEqual(
            size_result.configuration_id,
            momentum_result.configuration_id,
        )

    def test_identical_run_is_loaded_from_cache(self) -> None:
        training, inference = synthetic_panels()
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            second = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )

            self.assertEqual(first.cache_status, "generated")
            self.assertEqual(second.cache_status, "cached")
            self.assertEqual(first.result, second.result)
            payload = json.loads(
                Path(first.artifact_path).read_text(encoding="utf-8")
            )
            self.assertEqual(
                payload["run_artifact_version"],
                RUN_ARTIFACT_VERSION,
            )
            self.assertEqual(
                payload["configuration_id"],
                first.result.configuration_id,
            )
            self.assertIn("scikit-learn", payload["runtime_versions"])
            self.assertEqual(payload["created_by"], "local-research-user")
            events = [
                json.loads(line)
                for line in (
                    Path(directory) / "forecast_run_events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [event["cache_status"] for event in events],
                ["generated", "cached"],
            )
            self.assertTrue(
                all(
                    event["configuration_id"]
                    == first.result.configuration_id
                    for event in events
                )
            )
            self.assertEqual(
                payload["source_versions"]["data_version"],
                first.result.data_version,
            )
            self.assertEqual(payload["request"]["as_of_date"], "2022-12-31")
            self.assertTrue(first.walk_forward_path.is_file())
            self.assertEqual(
                first.walk_forward_rows,
                len(pd.read_parquet(first.walk_forward_path)),
            )
            self.assertEqual(
                payload["walk_forward_predictions"]["content_sha256"],
                first.walk_forward_sha256,
            )
            self.assertNotIn(
                "walk_forward_predictions",
                payload["result"],
            )
            self.assertEqual(
                len(
                    payload["result"]["walk_forward_diagnostics"][
                        "monthly_metrics"
                    ]
                ),
                6,
            )

    def test_implicit_and_explicit_latest_as_of_share_cache(self) -> None:
        training, inference = synthetic_panels()
        explicit = replace(request(), as_of_date="2022-12-31")
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            with patch.dict(
                "os.environ",
                {"FORECAST_RUN_ACTOR": "researcher@example.com"},
            ):
                second = execute_forecast(
                    training,
                    inference,
                    explicit,
                    directory,
                )

            self.assertEqual(
                first.result.configuration_id,
                second.result.configuration_id,
            )
            self.assertEqual(second.cache_status, "cached")
            self.assertEqual(second.actor, "researcher@example.com")
            self.assertEqual(second.created_by, "local-research-user")

    def test_force_refresh_verifies_without_replacing_cached_run(self) -> None:
        training, inference = synthetic_panels()
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            verified = execute_forecast(
                training,
                inference,
                request(),
                directory,
                force_refresh=True,
            )

            self.assertEqual(verified.cache_status, "verified")
            self.assertEqual(
                verified.result.configuration_id,
                first.result.configuration_id,
            )
            self.assertEqual(
                verified.created_at_utc,
                first.created_at_utc,
            )

    def test_corrupt_artifact_is_recomputed(self) -> None:
        training, inference = synthetic_panels()
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            Path(first.artifact_path).write_text("{broken", encoding="utf-8")

            repaired = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )

            self.assertEqual(repaired.cache_status, "repaired")
            self.assertEqual(repaired.cache_reason, "artifact is unreadable")

    def test_corrupt_walk_forward_artifact_is_recomputed(self) -> None:
        training, inference = synthetic_panels()
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            Path(first.walk_forward_path).write_bytes(b"broken")

            repaired = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )

            self.assertEqual(repaired.cache_status, "repaired")
            self.assertTrue(repaired.walk_forward_path.is_file())

    def test_mismatched_recomputation_does_not_replace_immutable_run(self) -> None:
        training, inference = synthetic_panels()
        with tempfile.TemporaryDirectory() as directory:
            first = execute_forecast(
                training,
                inference,
                request(),
                directory,
            )
            original = Path(first.artifact_path).read_bytes()
            mismatched = replace(
                first.result,
                expected_excess_return=(
                    first.result.expected_excess_return + 0.01
                ),
            )
            mismatched_computation = ForecastComputation(
                result=mismatched,
                walk_forward_predictions=pd.read_parquet(
                    first.walk_forward_path
                ).drop(columns=["configuration_id"]),
            )

            with patch(
                "excess_return_engine.runs.generate_forecast_computation",
                return_value=mismatched_computation,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "differs from its immutable cached run",
                ):
                    execute_forecast(
                        training,
                        inference,
                        request(),
                        directory,
                        force_refresh=True,
                    )

            self.assertEqual(
                Path(first.artifact_path).read_bytes(),
                original,
            )


if __name__ == "__main__":
    unittest.main()

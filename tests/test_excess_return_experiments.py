import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from excess_return_engine.experiments import (
    comparison_records,
    comparison_warnings,
    contribution_records,
    list_experiments,
    save_experiment,
)


def forecast_result(
    *,
    configuration_id: str = "run-a",
    permno: int = 1,
    factors: tuple[str, ...] = ("size",),
) -> SimpleNamespace:
    return SimpleNamespace(
        configuration_id=configuration_id,
        permno=permno,
        ticker="AAA",
        company="Alpha",
        as_of_date="2025-12-31",
        snapshot_source="latest_inference",
        replay_version=None,
        target_month="2026-01-31",
        benchmark_id="benchmark",
        selected_factors=factors,
        training_window_months=None,
        interval_level=0.8,
        expected_excess_return=0.01,
        probability_positive=0.55,
        interval_lower=-0.05,
        interval_upper=0.07,
        reliability=SimpleNamespace(
            model_reliability_score=65.0,
            model_reliability_label="Moderate",
            data_quality_score=79.0,
            data_quality_label="Moderate",
        ),
        validation_metrics={
            "oos_r2_vs_zero": 0.002,
            "interval_coverage": 0.79,
        },
        contributions=tuple(
            SimpleNamespace(factor_id=factor, contribution=0.001)
            for factor in factors
        ),
        data_version="data-v1",
        feature_version="feature-v1",
        target_version="target-v1",
        model_version="model-v1",
        reliability_version="reliability-v1",
        validation_version="validation-v1",
        walk_forward_version="walk-v1",
        walk_forward_diagnostics=SimpleNamespace(
            rmse=0.09,
            oos_r2_vs_zero=0.01,
            directional_hit_rate=0.52,
            interval_coverage=0.8,
            mean_rank_ic=0.03,
        ),
        lineage_version="lineage-v1",
        factor_lineage=SimpleNamespace(
            status="Research lag proxy",
            freshness_score=1.0,
            stale_factor_count=0,
            aging_factor_count=0,
            research_proxy_factor_count=1,
        ),
        audit_version="audit-v1",
        panel_audit=SimpleNamespace(
            audit_id="audit-123",
            status="Review required",
            blocking_issue_count=0,
            review_issue_count=2,
        ),
        challenger_version="challenger-v1",
        challenger_diagnostics=SimpleNamespace(
            leader_model_id="ols",
            metrics=(
                SimpleNamespace(model_id="zero", rmse=0.10),
                SimpleNamespace(model_id="elastic_net", rmse=0.08),
                SimpleNamespace(model_id="ols", rmse=0.07),
            ),
        ),
    )


class ExperimentTests(unittest.TestCase):
    def test_save_and_list_are_idempotent_for_name_and_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            timestamp = datetime(2026, 1, 1, tzinfo=UTC)
            first, first_path = save_experiment(
                forecast_result(),
                "Balanced baseline",
                directory,
                saved_at=timestamp,
            )
            second, second_path = save_experiment(
                forecast_result(),
                "  Balanced   baseline  ",
                directory,
                saved_at=timestamp,
            )

            self.assertEqual(first.experiment_id, second.experiment_id)
            self.assertEqual(first_path, second_path)
            listed = list_experiments(directory)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].name, "Balanced baseline")
            self.assertEqual(listed[0].selected_factors, ("size",))
            self.assertIsNone(listed[0].training_window_months)

    def test_comparison_warns_on_incompatible_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first, _ = save_experiment(
                forecast_result(configuration_id="run-a", permno=1),
                "First",
                directory,
            )
            second, _ = save_experiment(
                forecast_result(configuration_id="run-b", permno=2),
                "Second",
                directory,
            )

            warnings = comparison_warnings((first, second))

            self.assertIn(
                "Selected experiments use different company/security values.",
                warnings,
            )

    def test_comparison_and_contribution_records_keep_run_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            experiment, _ = save_experiment(
                forecast_result(factors=("size", "momentum_12_1")),
                "Two factors",
                directory,
            )

            comparison = comparison_records((experiment,))
            contributions = contribution_records((experiment,))

            self.assertEqual(comparison[0]["Run ID"], "run-a")
            self.assertEqual(comparison[0]["Factors"], 2)
            self.assertEqual(comparison[0]["Best holdout model"], "ols")
            self.assertEqual(comparison[0]["Production RMSE rank"], 2)
            self.assertEqual(comparison[0]["Walk-forward RMSE"], 0.09)
            self.assertEqual(
                comparison[0]["Factor lineage"],
                "Research lag proxy",
            )
            self.assertEqual(
                comparison[0]["Panel audit"],
                "Review required",
            )
            self.assertEqual(
                comparison[0]["Expected-return delta vs first"],
                0.0,
            )
            self.assertEqual(len(contributions), 2)

    def test_invalid_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "name is required"):
                save_experiment(forecast_result(), " ", directory)

    def test_v1_manifest_loads_as_all_available_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            experiment, path = save_experiment(
                forecast_result(),
                "Legacy",
                directory,
            )
            payload = experiment.to_dict()
            payload["experiment_version"] = "saved-experiment-v1"
            payload.pop("training_window_months")
            payload.pop("snapshot_source")
            payload.pop("replay_version")
            payload.pop("challenger_version")
            payload.pop("challenger_leader_model_id")
            payload.pop("production_rmse")
            payload.pop("production_rmse_rank")
            payload.pop("walk_forward_version")
            payload.pop("walk_forward_rmse")
            payload.pop("walk_forward_oos_r2")
            payload.pop("walk_forward_directional_hit_rate")
            payload.pop("walk_forward_interval_coverage")
            payload.pop("walk_forward_mean_rank_ic")
            payload.pop("lineage_version")
            payload.pop("factor_lineage_status")
            payload.pop("factor_freshness_score")
            payload.pop("stale_factor_count")
            payload.pop("aging_factor_count")
            payload.pop("research_proxy_factor_count")
            payload.pop("audit_version")
            payload.pop("panel_audit_id")
            payload.pop("panel_audit_status")
            payload.pop("audit_blocking_issue_count")
            payload.pop("audit_review_issue_count")
            Path(path).write_text(json.dumps(payload), encoding="utf-8")

            listed = list_experiments(directory)

            self.assertEqual(len(listed), 1)
            self.assertIsNone(listed[0].training_window_months)
            self.assertEqual(
                listed[0].snapshot_source,
                "latest_inference",
            )
            self.assertIsNone(listed[0].challenger_version)
            self.assertIsNone(listed[0].production_rmse)
            self.assertIsNone(listed[0].walk_forward_version)


if __name__ == "__main__":
    unittest.main()

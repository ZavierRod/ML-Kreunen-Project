import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from excess_return_engine.replay import ReplayOutcome
from ui.excess_return_engine import analyst


def forecast_result() -> SimpleNamespace:
    return SimpleNamespace(
        configuration_id="run-123",
        ticker="AAA",
        company="Alpha",
        permno=1,
        as_of_date="2025-12-31",
        target_month="2026-01-31",
        benchmark_id="test-benchmark",
        selected_factors=("size",),
        model_version="model-v1",
        feature_version="feature-v1",
        target_version="target-v1",
        data_version="data-v1",
        expected_excess_return=0.012,
        probability_positive=0.58,
        interval_level=0.80,
        interval_lower=-0.05,
        interval_upper=0.08,
        intercept=0.002,
        contributions=(
            SimpleNamespace(
                factor_id="size",
                normalized_value=0.8,
                coefficient=0.0125,
                contribution=0.01,
            ),
        ),
        current_regime=(
            SimpleNamespace(
                factor_id="size",
                normalized_value=0.8,
                percentile=0.9,
                regime="Top quintile",
            ),
        ),
        historical_evidence=SimpleNamespace(
            neighbor_count=2,
            mean_excess_return=0.01,
            median_excess_return=0.01,
            probability_positive=0.5,
            tenth_percentile=-0.02,
            ninetieth_percentile=0.04,
            analogs=(
                SimpleNamespace(
                    permno=2,
                    ticker="BBB",
                    company="Beta",
                    month_end="2024-01-31",
                    target_month="2024-02-29",
                    similarity=0.95,
                    observed_excess_return=0.03,
                ),
            ),
        ),
        validation_metrics={
            "oos_r2_vs_zero": 0.002,
            "interval_coverage": 0.79,
        },
        data_quality={
            "selected_factor_completeness": 1.0,
            "point_in_time_status": "research_lag_proxy",
        },
        challenger_diagnostics=SimpleNamespace(
            version="challenger-v1",
            leader_model_id="ols",
            sampled_training_rows=500,
            evaluation_rows=100,
            metrics=(
                SimpleNamespace(
                    model_id="elastic_net",
                    label="Production Elastic Net",
                    training_rows=1_000,
                    evaluation_rows=100,
                    mae=0.08,
                    rmse=0.10,
                    directional_hit_rate=0.51,
                    oos_r2_vs_zero=0.01,
                ),
                SimpleNamespace(
                    model_id="ols",
                    label="Ordinary least squares",
                    training_rows=500,
                    evaluation_rows=100,
                    mae=0.07,
                    rmse=0.09,
                    directional_hit_rate=0.53,
                    oos_r2_vs_zero=0.03,
                ),
            ),
        ),
    )


class _FakeResponses:
    def __init__(self) -> None:
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "forecast_run_id": "model-invented-id",
                    "answer": (
                        "The supplied excess-return forecast is modest. The "
                        "prediction interval is wide. Validation remains limited."
                    ),
                    "supporting_points": [],
                    "caveats": ["Research output."],
                    "suggested_followups": [
                        "Which factor contributes the most?",
                        "How did similar conditions perform?",
                    ],
                }
            )
        )


class _RetryResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            answer = {
                "forecast_run_id": "run-123",
                "answer": "This creates a negative outlook.",
                "supporting_points": [],
                "caveats": [],
                "suggested_followups": [
                    "Which market conditions could reverse the forecast?"
                ],
            }
        else:
            answer = {
                "forecast_run_id": "run-123",
                "answer": (
                    "The point estimate is a negative excess return relative to "
                    "the benchmark. The prediction interval is wide. The validation "
                    "evidence indicates that uncertainty should remain explicit."
                ),
                "supporting_points": [],
                "caveats": ["Research output."],
                "suggested_followups": [
                    "Which selected factor has the largest contribution?"
                ],
            }
        return SimpleNamespace(output_text=json.dumps(answer))


class _AlwaysInvalidResponses:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "forecast_run_id": "run-123",
                    "answer": "This is a favorable outlook.",
                    "supporting_points": [],
                    "caveats": [],
                    "suggested_followups": [
                        "Which market conditions could change this?"
                    ],
                }
            )
        )


class ForecastAnalystTests(unittest.TestCase):
    def test_context_excludes_individual_analogs_by_default(self) -> None:
        context = analyst.build_forecast_context(forecast_result())

        self.assertEqual(context["forecast_run"]["id"], "run-123")
        self.assertNotIn("analogs", context["historical_evidence"])
        self.assertFalse(
            context["historical_evidence"]["individual_rows_included"]
        )
        self.assertEqual(
            context["factor_evidence"][0]["cross_sectional_percentile"],
            0.9,
        )
        self.assertEqual(
            context["forecast"]["expected_excess_return_display"],
            "+1.20%",
        )
        self.assertEqual(
            context["historical_evidence"]["probability_positive_display"],
            "50.00%",
        )
        self.assertIn(
            "calibration residual",
            context["forecast"]["probability_method"],
        )
        self.assertEqual(
            context["challenger_diagnostics"]["leader_model_id"],
            "ols",
        )
        self.assertEqual(
            context["challenger_diagnostics"]["forecast_source"],
            "elastic_net",
        )

    def test_context_can_include_analog_rows_explicitly(self) -> None:
        context = analyst.build_forecast_context(
            forecast_result(),
            include_analog_rows=True,
        )

        self.assertEqual(
            context["historical_evidence"]["analogs"][0]["ticker"],
            "BBB",
        )

    def test_context_includes_compact_factor_lineage(self) -> None:
        result = forecast_result()
        result.lineage_version = "factor-lineage-v1"
        result.factor_lineage = SimpleNamespace(
            version="factor-lineage-v1",
            status="Verified",
            freshness_score=1.0,
            stale_factor_count=0,
            aging_factor_count=0,
            research_proxy_factor_count=0,
            factors=(
                SimpleNamespace(
                    factor_id="size",
                    source_system="wrds-derived-research-panel",
                    source_snapshot="data-v1",
                    source_values=(
                        SimpleNamespace(column="market_cap", value=100.0),
                    ),
                    observation_date="2025-12-31",
                    period_end_date="2025-12-31",
                    available_at="2025-12-31",
                    freshness_status="Current",
                    point_in_time_status="month_end_observed",
                    availability_rule="Observed at month end.",
                    warnings=(),
                ),
            ),
        )

        context = analyst.build_forecast_context(result)

        self.assertEqual(context["factor_lineage"]["status"], "Verified")
        self.assertEqual(
            context["factor_lineage"]["factors"][0]["source_values"],
            {"market_cap": 100.0},
        )

    def test_context_includes_post_forecast_replay_outcome(self) -> None:
        context = analyst.build_forecast_context(
            forecast_result(),
            replay_outcome=ReplayOutcome(
                permno=1,
                as_of_date="2025-12-31",
                target_month="2026-01-31",
                realized_excess_return=0.03,
                realized_stock_return=0.04,
                realized_benchmark_return=0.01,
            ),
        )

        replay = context["replay_evaluation"]
        self.assertTrue(replay["outcome_joined_after_forecast"])
        self.assertAlmostEqual(replay["forecast_error"], -0.018)

    def test_context_includes_walk_forward_evidence(self) -> None:
        result = forecast_result()
        result.walk_forward_diagnostics = SimpleNamespace(
            version="walk-v1",
            evaluation_start="2024-01-31",
            evaluation_end="2025-12-31",
            evaluation_months=24,
            evaluation_rows=100,
            calibration_residual_rows=80,
            mae=0.08,
            rmse=0.12,
            directional_hit_rate=0.52,
            brier_score=0.249,
            interval_coverage=0.79,
            oos_r2_vs_zero=0.01,
            mean_rank_ic=0.03,
            monthly_metrics=(
                SimpleNamespace(
                    as_of_date="2025-12-31",
                    target_month="2026-01-31",
                    training_rows=1_000,
                    evaluation_rows=100,
                    mae=0.08,
                    rmse=0.12,
                    directional_hit_rate=0.52,
                    brier_score=0.249,
                    interval_coverage=0.79,
                    rank_ic=0.03,
                ),
            ),
        )

        context = analyst.build_forecast_context(result)

        evidence = context["walk_forward_evaluation"]
        self.assertEqual(evidence["evaluation_months"], 24)
        self.assertEqual(evidence["monthly_metrics"][0]["rank_ic"], 0.03)
        self.assertIn("only earlier", evidence["method"])

    def test_api_call_is_non_stored_and_run_id_is_immutable(self) -> None:
        fake_responses = _FakeResponses()
        client = SimpleNamespace(responses=fake_responses)
        context = analyst.build_forecast_context(forecast_result())

        answer = analyst.answer_forecast_question(
            question="What is the main takeaway?",
            context=context,
            api_key="unused-test-key",
            model="test-model",
            client=client,
        )

        self.assertEqual(answer["forecast_run_id"], "run-123")
        self.assertFalse(fake_responses.arguments["store"])
        self.assertEqual(
            fake_responses.arguments["metadata"]["forecast_run_id"],
            "run-123",
        )
        self.assertEqual(
            fake_responses.arguments["text"]["format"]["type"],
            "json_schema",
        )
        self.assertIn(
            "negative excess-return forecast is not a forecast",
            fake_responses.arguments["instructions"],
        )
        self.assertIn(
            "answered completely from the supplied context",
            fake_responses.arguments["instructions"],
        )
        self.assertIn(
            "Use neutral statistical language",
            fake_responses.arguments["instructions"],
        )
        payload = json.loads(fake_responses.arguments["input"])
        self.assertEqual(payload["forecast_context"]["forecast_run"]["id"], "run-123")

    def test_question_validation_blocks_empty_and_oversized_input(self) -> None:
        context = analyst.build_forecast_context(forecast_result())
        client = SimpleNamespace(responses=_FakeResponses())

        with self.assertRaisesRegex(ValueError, "Enter a question"):
            analyst.answer_forecast_question(
                question=" ",
                context=context,
                api_key="unused",
                model="test",
                client=client,
            )
        with self.assertRaisesRegex(ValueError, "2,000"):
            analyst.answer_forecast_question(
                question="x" * 2_001,
                context=context,
                api_key="unused",
                model="test",
                client=client,
            )

    def test_noncompliant_answer_is_retried_once(self) -> None:
        responses = _RetryResponses()
        context = analyst.build_forecast_context(forecast_result())

        answer = analyst.answer_forecast_question(
            question="What is the takeaway?",
            context=context,
            api_key="unused",
            model="test",
            client=SimpleNamespace(responses=responses),
        )

        self.assertEqual(len(responses.calls), 2)
        self.assertNotIn("outlook", answer["answer"])
        self.assertEqual(answer["generation_mode"], "llm")
        retry_payload = json.loads(responses.calls[1]["input"])
        self.assertIn("required_corrections", retry_payload)

    def test_repeated_policy_failure_uses_deterministic_fallback(self) -> None:
        responses = _AlwaysInvalidResponses()
        context = analyst.build_forecast_context(forecast_result())

        answer = analyst.answer_forecast_question(
            question="What is the takeaway?",
            context=context,
            api_key="unused",
            model="test",
            client=SimpleNamespace(responses=responses),
        )

        self.assertEqual(responses.calls, 3)
        self.assertEqual(
            answer["generation_mode"],
            "deterministic_policy_fallback",
        )
        self.assertIn("+1.20% one-month excess return", answer["answer"])
        self.assertEqual(len(answer["suggested_followups"]), 3)

    def test_policy_rejects_ambiguous_absolute_return_language(self) -> None:
        violations = analyst._answer_policy_violations(
            {
                "answer": (
                    "The stock price will decline. Investors may face challenges. "
                    "This is a confidence interval."
                ),
                "supporting_points": [],
                "suggested_followups": [
                    "Which market conditions could reverse the forecast?"
                ],
            },
            question="What is the takeaway?",
        )

        self.assertGreaterEqual(len(violations), 5)

    def test_exchange_audit_is_local_jsonl_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = analyst.save_analyst_exchange(
                output_dir=directory,
                forecast_run_id="run-123",
                question="What is the takeaway?",
                model="test-model",
                include_analog_rows=False,
                answer={"forecast_run_id": "run-123", "answer": "Test answer."},
            )

            self.assertEqual(
                path,
                Path(directory).resolve() / "run-123.analyst.jsonl",
            )
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["forecast_run_id"], "run-123")
            self.assertEqual(record["model"], "test-model")
            self.assertNotIn("api_key", record)
            self.assertFalse(record["individual_analog_rows_sent"])


if __name__ == "__main__":
    unittest.main()

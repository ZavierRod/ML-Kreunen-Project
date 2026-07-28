import unittest
from types import SimpleNamespace

import pandas as pd

from ui.excess_return_engine.presentation import (
    apply_pending_saved_configuration,
    calibration_table,
    challenger_diagnostics_table,
    company_options,
    configuration_quality,
    correlation_warning_table,
    factor_option_label,
    factor_lineage_table,
    experiment_comparison_table,
    experiment_contribution_table,
    historical_analog_table,
    panel_audit_table,
    predictive_strength_label,
    queue_saved_configuration,
    reliability_component_table,
    regime_summary,
    regime_table,
    walk_forward_monthly_table,
    yearly_validation_table,
)


class PresentationTests(unittest.TestCase):
    def test_saved_configuration_is_deferred_until_next_run(self) -> None:
        state = {
            "forecast_as_of": "2025-12-31",
            "excess_return_result": object(),
            "forecast_execution_metadata": {"cache_status": "cached"},
        }
        saved = SimpleNamespace(
            as_of_date="2024-12-31",
            selected_factors=("size", "momentum_12_1"),
            interval_level=0.9,
            training_window_months=120,
            name="Historical replay",
            configuration_id="abc123",
        )

        queue_saved_configuration(state, saved, "GOOGL · Alphabet")

        self.assertEqual(state["forecast_as_of"], "2025-12-31")
        self.assertTrue(apply_pending_saved_configuration(state))
        self.assertEqual(state["forecast_as_of"], "2024-12-31")
        self.assertEqual(state["forecast_training_window"], 120)
        self.assertEqual(
            state["forecast_factors"],
            ["size", "momentum_12_1"],
        )
        self.assertNotIn("excess_return_result", state)
        self.assertNotIn("forecast_execution_metadata", state)
        self.assertFalse(apply_pending_saved_configuration(state))

    def test_company_options_use_permanent_identifier(self) -> None:
        inference = pd.DataFrame(
            [
                {"permno": 2, "ticker": "BBB", "company": "Beta"},
                {"permno": 1, "ticker": "AAA", "company": "Alpha"},
            ]
        )

        options = company_options(inference)

        self.assertEqual(
            options,
            [
                ("AAA · Alpha · PERMNO 1", 1),
                ("BBB · Beta · PERMNO 2", 2),
            ],
        )

    def test_configuration_quality_blocks_missing_current_factors(self) -> None:
        months = pd.date_range("2015-01-31", periods=120, freq="ME")
        training = pd.DataFrame(
            {
                "month_end": months,
                "size": 1.0,
                "momentum_12_1": 0.1,
                "excess_return_next_month": 0.01,
            }
        )
        inference = pd.DataFrame(
            [
                {
                    "permno": 1,
                    "size": 1.0,
                    "momentum_12_1": pd.NA,
                }
            ]
        )

        quality = configuration_quality(
            training,
            inference,
            1,
            ("size", "momentum_12_1"),
        )

        self.assertEqual(quality["status"], "blocked")
        self.assertEqual(quality["current_completeness"], 0.5)

    def test_configuration_quality_flags_correlated_selected_factors(self) -> None:
        months = pd.date_range("2015-01-31", periods=120, freq="ME")
        training = pd.DataFrame(
            {
                "month_end": months,
                "size": range(120),
                "momentum_12_1": range(120),
                "excess_return_next_month": 0.01,
            }
        )
        inference = pd.DataFrame(
            [{"permno": 1, "size": 1.0, "momentum_12_1": 1.0}]
        )

        quality = configuration_quality(
            training,
            inference,
            1,
            ("size", "momentum_12_1"),
        )

        self.assertEqual(len(quality["correlated_pairs"]), 1)

    def test_configuration_quality_excludes_rows_on_or_after_as_of(self) -> None:
        months = pd.date_range("2015-01-31", periods=130, freq="ME")
        training = pd.DataFrame(
            {
                "month_end": months,
                "size": 1.0,
                "excess_return_next_month": 0.01,
            }
        )
        inference = pd.DataFrame(
            [
                {
                    "permno": 1,
                    "size": 1.0,
                    "market_cap": 100.0,
                    "source_last_trading_date": months[120],
                }
            ]
        )

        quality = configuration_quality(
            training,
            inference,
            1,
            ("size",),
            as_of_date=months[120],
        )

        self.assertEqual(quality["status"], "ready")
        self.assertEqual(quality["training_months"], 120)
        self.assertEqual(quality["training_rows"], 120)
        self.assertEqual(quality["factor_lineage"].status, "Verified")

    def test_factor_lineage_table_exposes_source_evidence(self) -> None:
        result = SimpleNamespace(
            factor_lineage=SimpleNamespace(
                factors=(
                    SimpleNamespace(
                        label="Size",
                        category="Market",
                        raw_value=10.0,
                        normalized_value=0.5,
                        observation_date="2025-12-31",
                        period_end_date="2025-12-31",
                        available_at="2025-12-31",
                        age_days=0,
                        freshness_status="Current",
                        point_in_time_status="month_end_observed",
                        source_values=(
                            SimpleNamespace(
                                column="market_cap",
                                value=100.0,
                            ),
                        ),
                    ),
                )
            )
        )

        table = factor_lineage_table(result)

        self.assertEqual(table.iloc[0]["Factor"], "Size")
        self.assertIn("market_cap=100.0", table.iloc[0]["Source evidence"])

    def test_panel_audit_table_exposes_contract_checks(self) -> None:
        result = SimpleNamespace(
            panel_audit=SimpleNamespace(
                checks=(
                    SimpleNamespace(
                        label="Inference outcome isolation",
                        status="Pass",
                        severity="blocking",
                        observed="0 populated outcome cells",
                        detail="Inference outcomes must be empty.",
                    ),
                )
            )
        )

        table = panel_audit_table(result)

        self.assertEqual(
            table.iloc[0]["Check"],
            "Inference outcome isolation",
        )
        self.assertEqual(table.iloc[0]["Status"], "Pass")

    def test_factor_labels_and_predictive_strength_are_explicit(self) -> None:
        self.assertEqual(factor_option_label("size"), "Size · Market")
        self.assertEqual(
            predictive_strength_label(
                {"oos_r2_vs_zero": 0.002, "directional_hit_rate": 0.50}
            ),
            "Modest",
        )

    def test_regime_and_analog_tables_are_readable(self) -> None:
        result = SimpleNamespace(
            current_regime=(
                SimpleNamespace(
                    factor_id="size",
                    normalized_value=0.8,
                    percentile=0.9,
                    regime="Top quintile",
                ),
                SimpleNamespace(
                    factor_id="momentum_12_1",
                    normalized_value=-0.6,
                    percentile=0.2,
                    regime="Bottom quintile",
                ),
            ),
            historical_evidence=SimpleNamespace(
                analogs=(
                    SimpleNamespace(
                        ticker="AAA",
                        company="Alpha",
                        month_end="2024-01-31",
                        target_month="2024-02-29",
                        similarity=0.95,
                        observed_excess_return=0.02,
                    ),
                )
            ),
        )

        self.assertEqual(
            regime_summary(result),
            "Top quintile Size · Bottom quintile 12-1 momentum",
        )
        self.assertEqual(regime_table(result).iloc[0]["Factor"], "Size")
        self.assertEqual(historical_analog_table(result).iloc[0]["Ticker"], "AAA")

    def test_reliability_tables_expose_components_and_correlations(self) -> None:
        result = SimpleNamespace(
            reliability=SimpleNamespace(
                components=(
                    SimpleNamespace(
                        component="Interval calibration",
                        score=92.0,
                        status="Strong",
                        value="79% realized",
                        detail="Coverage definition.",
                    ),
                ),
                correlated_factor_pairs=(
                    SimpleNamespace(
                        factor_a="size",
                        factor_b="momentum_12_1",
                        correlation=0.88,
                    ),
                ),
            )
        )

        self.assertEqual(
            reliability_component_table(result).iloc[0]["Status"],
            "Strong",
        )
        self.assertEqual(
            correlation_warning_table(result).iloc[0]["Factor A"],
            "Size",
        )

    def test_validation_diagnostic_tables_are_readable(self) -> None:
        result = SimpleNamespace(
            validation_diagnostics=SimpleNamespace(
                calibration_bins=(
                    SimpleNamespace(
                        bin_number=1,
                        rows=10,
                        minimum_probability=0.1,
                        maximum_probability=0.2,
                        mean_predicted_probability=0.15,
                        observed_positive_rate=0.2,
                    ),
                ),
                yearly_metrics=(
                    SimpleNamespace(
                        outcome_year=2025,
                        rows=10,
                        mae=0.04,
                        rmse=0.06,
                        directional_hit_rate=0.52,
                        interval_coverage=0.8,
                        mean_actual_excess_return=0.01,
                        mean_predicted_excess_return=0.005,
                    ),
                ),
            )
        )

        self.assertEqual(calibration_table(result).iloc[0]["Rows"], 10)
        self.assertEqual(
            yearly_validation_table(result).iloc[0]["Outcome year"],
            2025,
        )

    def test_walk_forward_monthly_table_is_readable(self) -> None:
        result = SimpleNamespace(
            walk_forward_diagnostics=SimpleNamespace(
                monthly_metrics=(
                    SimpleNamespace(
                        as_of_date="2025-11-30",
                        target_month="2025-12-31",
                        training_rows=1_000,
                        evaluation_rows=100,
                        mae=0.08,
                        rmse=0.12,
                        directional_hit_rate=0.52,
                        brier_score=0.249,
                        interval_coverage=0.79,
                        rank_ic=0.03,
                        mean_actual_excess_return=0.01,
                        mean_predicted_excess_return=0.005,
                    ),
                ),
            )
        )

        table = walk_forward_monthly_table(result)

        self.assertEqual(table.iloc[0]["As of"], "2025-11-30")
        self.assertEqual(table.iloc[0]["Rank IC"], 0.03)

    def test_experiment_comparison_uses_factor_labels(self) -> None:
        experiment = SimpleNamespace(
            name="Baseline",
            configuration_id="abcdef123",
            ticker="AAA",
            permno=1,
            selected_factors=("size",),
            snapshot_source="latest_inference",
            training_window_months=None,
            expected_excess_return=0.01,
            probability_positive=0.55,
            interval_lower=-0.05,
            interval_upper=0.07,
            model_reliability_score=65.0,
            data_quality_score=79.0,
            oos_r2_vs_zero=0.002,
            interval_coverage=0.8,
            challenger_leader_model_id="ols",
            production_rmse=0.12,
            production_rmse_rank=2,
            walk_forward_rmse=0.09,
            walk_forward_oos_r2=0.01,
            walk_forward_directional_hit_rate=0.52,
            walk_forward_interval_coverage=0.8,
            walk_forward_mean_rank_ic=0.03,
            contributions=(
                SimpleNamespace(factor_id="size", contribution=0.001),
            ),
        )

        comparison = experiment_comparison_table((experiment,))
        contributions = experiment_contribution_table((experiment,))

        self.assertEqual(comparison.iloc[0]["Factor set"], "Size")
        self.assertEqual(contributions.iloc[0]["Factor"], "Size")

    def test_legacy_experiment_comparison_can_format_missing_challengers(
        self,
    ) -> None:
        experiment = SimpleNamespace(
            name="Legacy",
            configuration_id="legacy123",
            ticker="AAA",
            permno=1,
            selected_factors=("size",),
            snapshot_source="latest_inference",
            expected_excess_return=0.01,
            probability_positive=0.55,
            interval_lower=-0.05,
            interval_upper=0.07,
            model_reliability_score=65.0,
            data_quality_score=79.0,
            oos_r2_vs_zero=0.002,
            interval_coverage=0.8,
            training_window_months=None,
            challenger_leader_model_id=None,
            production_rmse=None,
            production_rmse_rank=None,
            walk_forward_rmse=None,
            walk_forward_oos_r2=None,
            walk_forward_directional_hit_rate=None,
            walk_forward_interval_coverage=None,
            walk_forward_mean_rank_ic=None,
            contributions=(),
        )

        table = experiment_comparison_table((experiment,))
        styled = table.style.format(
            {"Production RMSE": "{:.2%}"},
            na_rep="Not recorded",
        )

        self.assertIn("Not recorded", styled.to_html())

    def test_challenger_table_marks_production_and_leader(self) -> None:
        result = SimpleNamespace(
            challenger_diagnostics=SimpleNamespace(
                leader_model_id="ols",
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
            )
        )

        table = challenger_diagnostics_table(result)

        leader = table.loc[table["Best RMSE"]].iloc[0]
        production = table.loc[table["Role"] == "Production"].iloc[0]
        self.assertEqual(leader["Model"], "Ordinary least squares")
        self.assertAlmostEqual(production["RMSE vs production"], 0.0)


if __name__ == "__main__":
    unittest.main()

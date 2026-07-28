import unittest

import numpy as np
import pandas as pd

from excess_return_engine.audit import (
    AUDIT_VERSION,
    audit_forecast_panels,
)


def audit_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    historical = pd.DataFrame(
        [
            {
                "permno": 1,
                "month_end": "2025-10-31",
                "target_month": "2025-11-30",
                "benchmark_id": "benchmark",
                "stock_return_next_month": 0.03,
                "benchmark_return": 0.01,
                "excess_return_next_month": 0.02,
                "source_last_trading_date": "2025-10-31",
                "fund_available_date": "2025-09-30",
            }
        ]
    )
    inference = pd.DataFrame(
        [
            {
                "permno": 1,
                "month_end": "2025-11-30",
                "target_month": "2025-12-31",
                "benchmark_id": "benchmark",
                "stock_return_next_month": np.nan,
                "benchmark_return": np.nan,
                "excess_return_next_month": np.nan,
                "source_last_trading_date": "2025-11-28",
                "fund_available_date": "2025-09-30",
            }
        ]
    )
    return historical, inference


class PanelAuditTests(unittest.TestCase):
    def test_valid_research_panel_passes_blocking_checks(self) -> None:
        historical, inference = audit_panels()

        audit = audit_forecast_panels(
            historical,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("size",),
        )

        self.assertEqual(audit.version, AUDIT_VERSION)
        self.assertEqual(audit.status, "Review required")
        self.assertEqual(audit.blocking_issue_count, 0)
        self.assertEqual(audit.review_issue_count, 1)
        self.assertEqual(audit.selected_factors, ("size",))
        self.assertEqual(len(audit.audit_id), 16)
        self.assertEqual(len(audit.scope_content_sha256), 64)

    def test_audit_identity_changes_with_audited_content(self) -> None:
        historical, inference = audit_panels()
        first = audit_forecast_panels(
            historical,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("size",),
        )
        changed = historical.copy()
        changed.loc[0, "stock_return_next_month"] += 0.01
        changed.loc[0, "excess_return_next_month"] += 0.01

        second = audit_forecast_panels(
            changed,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("size",),
        )

        self.assertNotEqual(first.audit_id, second.audit_id)
        self.assertNotEqual(
            first.scope_content_sha256,
            second.scope_content_sha256,
        )

    def test_leaked_inference_outcome_is_blocked(self) -> None:
        historical, inference = audit_panels()
        inference.loc[0, "excess_return_next_month"] = 0.04

        with self.assertRaisesRegex(
            ValueError,
            "Inference outcome isolation",
        ):
            audit_forecast_panels(
                historical,
                inference,
                as_of_date="2025-11-30",
                benchmark_id="benchmark",
                selected_factors=("size",),
            )

    def test_unreconciled_target_is_blocked(self) -> None:
        historical, inference = audit_panels()
        historical.loc[0, "excess_return_next_month"] = 0.50

        audit = audit_forecast_panels(
            historical,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("size",),
            strict=False,
        )

        self.assertEqual(audit.status, "Blocked")
        self.assertEqual(audit.blocking_issue_count, 1)

    def test_fundamental_selection_discloses_proxy(self) -> None:
        historical, inference = audit_panels()

        audit = audit_forecast_panels(
            historical,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("asset_growth",),
        )

        checks = {check.check_id: check for check in audit.checks}
        self.assertEqual(checks["fundamental_availability"].status, "Review")
        self.assertEqual(audit.review_issue_count, 2)

    def test_selected_factor_missing_source_date_is_blocked(self) -> None:
        historical, inference = audit_panels()
        historical["size"] = 1.0
        historical.loc[0, "source_last_trading_date"] = np.nan

        with self.assertRaisesRegex(
            ValueError,
            "Source-date completeness",
        ):
            audit_forecast_panels(
                historical,
                inference,
                as_of_date="2025-11-30",
                benchmark_id="benchmark",
                selected_factors=("size",),
            )

    def test_verified_delisting_integration_clears_review(self) -> None:
        historical, inference = audit_panels()
        historical["delisting_return_included"] = True

        audit = audit_forecast_panels(
            historical,
            inference,
            as_of_date="2025-11-30",
            benchmark_id="benchmark",
            selected_factors=("size",),
        )

        self.assertEqual(audit.status, "Passed")
        self.assertEqual(audit.review_issue_count, 0)


if __name__ == "__main__":
    unittest.main()

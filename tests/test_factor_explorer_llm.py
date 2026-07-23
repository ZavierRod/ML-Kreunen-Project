import unittest

import pandas as pd

from ui.factor_explorer import llm


class SectionOverviewContextTests(unittest.TestCase):
    def test_context_includes_selected_period_and_table_shape(self) -> None:
        panel = pd.DataFrame(
            [
                {
                    "period": "2023-2024",
                    "metric": "Revenue",
                    "type": "factor",
                    "pct_change": 0.2,
                    "weight": 1.0,
                }
            ]
        )
        detail = pd.DataFrame(
            [
                {
                    "from_year": 2023,
                    "to_year": 2024,
                    "period": "2023-2024",
                    "Revenue pct": 0.2,
                }
            ]
        )
        comparison = pd.DataFrame(
            [
                {
                    "preset": "Current selection",
                    "factor_count": 1,
                    "mode": "weighted",
                    "top_metric": "Revenue",
                    "top_mean_abs": 0.2,
                    "valid_periods": 1,
                    "conflicts": "",
                }
            ]
        )

        context = llm.build_section_overview_context(
            analysis_context={"scope": {"company": "GOOG"}},
            panel=panel,
            detail=detail,
            preset_comparison=comparison,
            selected_period="2023-2024",
        )

        views = context["section_views"]
        self.assertEqual(
            views["period_drilldown"]["selected_period"],
            "2023-2024",
        )
        self.assertEqual(len(views["period_drilldown"]["rows"]), 1)
        self.assertEqual(views["per_period_detail"]["row_count"], 1)
        self.assertEqual(
            views["visual_analysis"]["preset_comparison"][0]["top_metric"],
            "Revenue",
        )

        ranking_context = llm.context_for_section_overview(context, "ranking_table")
        period_context = llm.context_for_section_overview(context, "period_drilldown")
        visual_context = llm.context_for_section_overview(context, "visual_analysis")

        self.assertNotIn("period_panel", ranking_context)
        self.assertEqual(
            period_context["section_view"]["selected_period"],
            "2023-2024",
        )
        self.assertIn("period_panel", visual_context)

    def test_unknown_section_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown section overview"):
            llm.context_for_section_overview({}, "unknown")


if __name__ == "__main__":
    unittest.main()

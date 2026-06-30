# Replication And Expansion Section

## Goal Of This Section

This section should do 2 things:

1. Show that you successfully replicated and expanded the original formulas-sheet methodology.
2. Show how `Rev/S` and `Net Margin` contributed to EPS across the requested windows.

To keep the presentation clean, this section should be **3 slides total**.

The best way to do that, based on the codebase, is:

- use `scripts/phase2_eps_expansion.py` to explain the methodology expansion
- use `outputs/phase4/phase4_eps_two_factor_yoy.csv` and `reports/EPS-analysis-question-answers.md` for the final contribution tables

That works because:

- `Phase 2` is where the original sheet logic was extended
- `Phase 4` is where the exact year-over-year 2-factor bridge was formatted into presentation-ready answers

---

## The 3-Slide Version

## Slide 1

### Title

`Replication And Expansion: Method And Validation`

### Exact Wording To Put On The Slide

Use this text exactly as the main body:

> I first replicated the original formulas-sheet method for the `2015-2020` sample, then expanded the same logic to three longer windows: `2015-2025`, `2010-2025`, and `2001-2025`. After that, I used the exact year-over-year two-factor bridge to show how `Rev/S` and `Net Margin` contributed to EPS in each period.

### What To Include On The Slide

Use 3 blocks on the slide.

#### Block 1: workflow

Put these bullets on the left:

- Replicate the original `Sheet1.csv` logic
- Expand the logic to `2015-2025`, `2010-2025`, and `2001-2025`
- Build year-over-year `Rev/S` and `Net Margin` contribution tables
- Use those tables to interpret EPS drivers by window

#### Block 2: formulas

Put these formulas in the center or right:

```text
EPS = Rev/S x Net Margin
Rev/S = Revenue / Shares
Net Margin = Net Income / Revenue
```

#### Block 3: validation mini-table

Use this table:

| Check                  | Result |
| ---                    | ---    |
| `2015_2025` row counts | PASS   |
| `2010_2025` row counts | PASS   |
| `2001_2025` row counts | PASS   |
| Phase 1 formulas-sheet tie-out inside Phase 2 | PASS |

Source:

- `outputs/phase2/phase2_validation_results.csv`

### Optional Small Footer Note

Put this at the bottom in smaller text:

> `Phase 2` expands the original formula-sheet method. `Phase 4` converts the same two-factor logic into exact year-over-year contribution tables.

### What Code To Include

Include only this one short snippet on the slide or in a small appendix box:

```python
delta_rev_per_share = (
    current["rev_per_share"] / base["rev_per_share"]
) ** (1 / horizon_years) - 1
delta_net_margin = (
    current["net_margin"] / base["net_margin"]
) ** (1 / horizon_years) - 1
delta_eps_sheet_logic = delta_rev_per_share + delta_net_margin
```

Source:

- `scripts/phase2_eps_expansion.py`

This is the best code to show because it directly proves how the original formulas-sheet method was expanded.

### What To Say Out Loud

Use this:

> The original spreadsheet only covered the 2015 to 2020 sample. I first replicated that to confirm the logic was correct. Then I extended the same method to the three required windows. Finally, I used the exact year-over-year two-factor bridge to show how revenue per share and net margin drove EPS period by period.

---

## Slide 2

### Title

`Years 1-10 And Years 1-15: 2015-2025 And 2010-2025`

### Exact Wording To Put On The Slide

Put this text above the tables:

> In the cleanest modern window (`2015-2025`), `Rev/S` and `Net Margin` split dominance evenly. When the window expands back to `2010`, `Rev/S` becomes the more frequent dominant driver, although margin still explains several large swings.

### What To Include On The Slide

Use **2 stacked tables** or **2 side-by-side tables**.

#### Table A: `2015-2025`

Use this exact table:

| Period | Rev/S Contribution | Net Margin Contribution | EPS Change | Dominant Driver |
| --- | ---: | ---: | ---: | --- |
| 2015-2016 | 0.1772 | -0.0103 | 0.1669 | rev_per_share |
| 2016-2017 | 0.2022 | -0.6361 | -0.4339 | net_margin |
| 2017-2018 | 0.2071 | 0.6764 | 0.8835 | net_margin |
| 2018-2019 | 0.1748 | -0.0571 | 0.1177 | rev_per_share |
| 2019-2020 | 0.1368 | 0.0390 | 0.1758 | rev_per_share |
| 2020-2021 | 0.3584 | 0.2909 | 0.6493 | rev_per_share |
| 2021-2022 | 0.1229 | -0.3306 | -0.2077 | net_margin |
| 2022-2023 | 0.1171 | 0.1242 | 0.2412 | net_margin |
| 2023-2024 | 0.1516 | 0.1752 | 0.3268 | net_margin |
| 2024-2025 | 0.1582 | 0.1372 | 0.2953 | rev_per_share |

#### Table B: `2010-2025`

Use a shortened version of the full table if space is tight, but keep these rows at minimum:

| Period | Rev/S Contribution | Net Margin Contribution | EPS Change | Dominant Driver |
| ---    |               ---: |                    ---: |       ---: |             --- |
| 2010-2011 | 0.2446 | -0.1215 | 0.1231 | rev_per_share |
| 2011-2012 | 0.2650 | -0.1827 | 0.0823 | rev_per_share |
| 2012-2013 | 0.0818 | 0.0693 | 0.1511 | rev_per_share |
| 2013-2014 | -2.8214 | -0.0684 | -2.8898 | rev_per_share |
| 2014-2015 | 0.1039 | 0.0177 | 0.1216 | rev_per_share |
| 2015-2016 | 0.1772 | -0.0103 | 0.1669 | rev_per_share |
| 2016-2017 | 0.2022 | -0.6361 | -0.4339 | net_margin |
| 2017-2018 | 0.2071 | 0.6764 | 0.8835 | net_margin |
| 2021-2022 | 0.1229 | -0.3306 | -0.2077 | net_margin |
| 2024-2025 | 0.1582 | 0.1372 | 0.2953 | rev_per_share |

If you have enough space, use the full `2010-2025` table from:

- `reports/EPS-analysis-question-answers.md`

### Summary Callout Box

Put this on the right side or bottom:

- `2015-2025`: `Rev/S` dominated 5 periods, `Net Margin` dominated 5 periods
- `2010-2025`: `Rev/S` dominated 10 periods, `Net Margin` dominated 5 periods
- `2013-2014` is a major outlier and should be interpreted cautiously

### What To Say Out Loud

Use this:

> In the `2015-2025` window, the results are very balanced: revenue per share and margin each dominate in five periods. Once the window expands back to `2010`, revenue per share becomes the more common driver. The main exception is the `2013-2014` period, which is unusually extreme and should be treated cautiously.

---

## Slide 3

### Title

`Years 1-20: 2001-2025 And Main Takeaways`

### Exact Wording To Put On The Slide

Put this text at the top:

> Across the full `2001-2025` history, `Rev/S` is the more frequent dominant two-factor driver. However, the `2013-2014` result is likely distorted by the share-basis break around 2014, so the cleanest interpretation still comes from the more recent windows.

### What To Include On The Slide

Do **not** put the full 24-row table on this slide. It will be too crowded.

Instead, include:

#### Block 1: summary mini-table

| Window | Periods | More Frequent Dominant Driver | Interpretation Quality |
| --- | ---: | --- | --- |
| `2015-2025` | 10 | Balanced: `Rev/S` 5, `Net Margin` 5 | Strongest |
| `2010-2025` | 15 | `Rev/S` | Good, with caution |
| `2001-2025` | 24 | `Rev/S` | Directional only |

#### Block 2: full-history highlights

Put these bullets:

- In the full `2001-2025` window, `Rev/S` dominated `16 of 24` periods.
- `Net Margin` dominated `8 of 24` periods.
- Strong positive early-history swings were often revenue-driven.
- The `2013-2014` period is the biggest outlier and should be caveated.

#### Block 3: caution box

Use this wording exactly:

> Caution: the `2013-2014` result is likely affected by a share-basis break around 2014, so long-history share-related conclusions should be treated carefully.

### Optional Small Appendix Reference

Put this in small text at the bottom:

> Full contribution tables are available in `reports/EPS-analysis-question-answers.md` and `outputs/phase4/phase4_eps_two_factor_yoy.csv`.

### What To Say Out Loud

Use this:

> Across the full history, revenue per share is the dominant two-factor driver more often than net margin. That suggests EPS growth was more often supported by scaling revenue per share than by margin improvement alone. However, the 2013 to 2014 result is a major outlier, so the safest business interpretation comes from the cleaner modern windows, especially 2015 to 2025.

---

## What To Actually Put In The Deck

If you want the simplest final instruction set, use exactly this:

- Slide 1: method + formulas + mini validation table + one short code snippet
- Slide 2: `2015-2025` full table + `2010-2025` shortened/full table + summary callouts
- Slide 3: `2001-2025` summary table + 4 bullets + caution box

That is the best 3-slide version.

---

## Best Files To Pull From

### For Slide 1

- `scripts/phase2_eps_expansion.py`
- `outputs/phase2/phase2_validation_results.csv`

### For Slide 2

- `reports/EPS-analysis-question-answers.md`
- `outputs/phase4/phase4_eps_two_factor_yoy.csv`

### For Slide 3

- `reports/EPS-analysis-question-answers.md`
- `outputs/phase4/phase4_eps_business_answers.md`
- `reports/EPS-analysis-executive-summary.md`

---

## Final Presenter Message

If you want one short closing statement for this section, use this:

> The replication and expansion results show that the original formulas-sheet methodology was successfully extended across all requested windows, but the clearest and most presentation-safe interpretation comes from the recent windows and the exact year-over-year two-factor bridge.

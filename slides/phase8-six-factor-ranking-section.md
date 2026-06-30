# Phase 8 Six-Factor Ranking Section

## Goal Of This Section

This section should do 2 things:

1. Show that the GOOG share data was normalized for the 20-for-1 split so the long history is consistent.
2. Rank and weight the six factors (Revenue, Net Margin, EPS, FCF, NetCash, Shares) so we know which ones move the most.

To keep the presentation clean, this section should be **3 slides total**.

The best way to do that, based on the codebase, is:

- use `scripts/phase8_six_factor_ranking.py` to explain the method
- use `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv` and `outputs/phase8/phase8_six_factor_ranking_recent5_2020_2025.csv` for the ranking tables
- use `outputs/phase8/phase8_six_factor_panel.csv` for the per-period worked example

---

## Plain-English Summary (read this first)

Two things happened in Phase 8:

1. **We fixed a data problem.** Google did a 20-for-1 stock split. In the model, the older years (2001-2013) were still counted on the pre-split basis, which made share counts look ~20x too small versus 2014 onward. We multiplied those older years by 20 so every year is on the same post-split basis. This removed a fake "share count crashed" spike that used to appear in 2013-2014.

2. **We ranked the six factors.** For every pair of adjacent years we measured how much each factor moved (simple percent change), gave each factor a weight equal to its share of the total movement that year, then ranked them by their average movement across the period. `Shares` barely moves; `EPS` moves the most.

---

## The 3-Slide Version

## Slide 1

### Title

`Normalizing The Data And Ranking The Factors`

### Exact Wording To Put On The Slide

Use this text exactly as the main body:

> Before ranking anything, I normalized the share data for Google's 20-for-1 split: the 2001-2013 share counts were on the old pre-split basis, so I restated them x20 to match 2014 onward. Then I ranked six factors (Revenue, Net Margin, EPS, FCF, NetCash, Shares) by how much each one moves year to year, weighting each factor by its share of the total movement in that period.

### What To Include On The Slide

Use 3 blocks on the slide.

#### Block 1: the split fix

Put these bullets on the left:

- Google split its stock `20-for-1`
- Pre-split years (`2001-2013`) were ~20x too small
- Restated those years `x20` to a consistent basis
- This removed a false `2013-2014` share-count spike

#### Block 2: the ranking method

Put these formulas in the center or right:

```text
pct change   = level_this_year / level_last_year - 1
factor weight = |pct change|  /  sum of |pct change| for all 6 factors
rank          = by average |pct change| across the period
```

#### Block 3: validation mini-table

Use this table:

| Check                                   | Result |
| ---                                     | ---    |
| `2001_2025` period count                | PASS   |
| Factor weights sum to 100%              | PASS   |
| NetCash matches the workbook's own row  | PASS   |
| Shares are split-consistent (no 20x jump) | PASS |

Source:

- `outputs/phase8/phase8_validation_results.csv`

### What To Say Out Loud

Use this:

> The first thing I had to do was fix the share data. Google did a twenty-for-one split, and the older years in the model were still on the old basis, which made them look twenty times too small. I restated those years so everything is comparable. Then I ranked the six factors by how much each one actually moves from year to year.

---

## Slide 2

### Title

`Which Factors Move The Most`

### Exact Wording To Put On The Slide

Put this text above the tables:

> Ranked by average year-over-year movement, EPS is the biggest mover over the full history, followed by the cash-flow and cash measures. Shares barely move at all, which is exactly what we expect from a company that only does modest buybacks.

### What To Include On The Slide

Use **2 side-by-side tables**.

#### Table A: Full History (2001-2025)

| Rank | Factor | Avg Move | Avg Weight |
| ---: | --- | ---: | ---: |
| 1 | EPS | 97.0% | 24.5% |
| 2 | NetCash | 85.4% | 18.1% |
| 3 | FCF | 66.1% | 22.7% |
| 4 | Revenue | 55.7% | 19.3% |
| 5 | Net Margin | 34.4% | 13.9% |
| 6 | Shares | 3.4% | 1.5% |

#### Table B: Recent 5 Years (2020-2025)

| Rank | Factor | Avg Move | Avg Weight |
| ---: | --- | ---: | ---: |
| 1 | EPS | 42.1% | 37.3% |
| 2 | Net Margin | 21.8% | 21.2% |
| 3 | Revenue | 17.7% | 15.1% |
| 4 | FCF | 17.6% | 13.2% |
| 5 | NetCash | 10.1% | 10.6% |
| 6 | Shares | 2.3% | 2.7% |

Source:

- `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv`
- `outputs/phase8/phase8_six_factor_ranking_recent5_2020_2025.csv`

### Summary Callout Box

Put this on the right side or bottom:

- `EPS` is the #1 mover in both windows
- The early years are noisier, so `NetCash` and `FCF` rank higher in the full history
- `Shares` is always the smallest mover (steady share count)

### What To Say Out Loud

Use this:

> EPS is the biggest mover in both the full history and the recent five years. Over the long history the cash measures rank high because the early years were small and volatile. The recent window is cleaner, and there margin and revenue rise toward the top. In every case, share count is the smallest mover.

---

## Slide 3

### Title

`How The Weighting Works And Main Takeaways`

### Exact Wording To Put On The Slide

Put this text at the top:

> Each year, every factor gets a weight equal to its share of the total movement. The example below shows the 2020-2021 period: EPS moved the most (91%), so it earns the largest weight.

### What To Include On The Slide

#### Block 1: worked example (2020-2021)

| Factor | Year-over-year Move | Weight |
| --- | ---: | ---: |
| EPS | +91.4% | 39.5% |
| FCF | +56.4% | 24.3% |
| Revenue | +41.2% | 17.8% |
| Net Margin | +33.8% | 14.6% |
| NetCash | +7.6% | 3.3% |
| Shares | -1.4% | 0.6% |

> Weights add to 100%. The factor that moves most that year carries the most weight.

#### Block 2: main takeaways

Put these bullets:

- The data is now split-consistent, so the long history is finally usable.
- `EPS` is the most active factor; `Shares` is the least active.
- Cash-based factors (`NetCash`, `FCF`) are large movers over the full history.
- This gives us a clean ranked, weighted factor set, ready for the next step.

#### Block 3: what is next

Use this wording exactly:

> Next step: with these six factors ranked and weighted, the framework is ready to bring in PRICE and test how these factors relate to it.

### Optional Small Appendix Reference

Put this in small text at the bottom:

> Full per-period detail is in `outputs/phase8/phase8_six_factor_panel.csv`; factor levels are in `outputs/phase8/phase8_factor_levels.csv`.

### What To Say Out Loud

Use this:

> The weighting is simple: each year, whichever factor moved the most gets the biggest weight, and the weights always add to one hundred percent. Across the whole history, EPS is the most active factor and share count is the quietest. Now that the data is normalized and the factors are ranked and weighted, the next step is to bring in price.

---

## What To Actually Put In The Deck

If you want the simplest final instruction set, use exactly this:

- Slide 1: the split fix + the ranking method + mini validation table
- Slide 2: the two ranking tables + summary callouts
- Slide 3: the 2020-2021 worked example + 4 takeaways + "what is next" box

That is the best 3-slide version.

---

## Best Files To Pull From

### For Slide 1

- `scripts/phase8_six_factor_ranking.py`
- `outputs/phase8/phase8_validation_results.csv`

### For Slide 2

- `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv`
- `outputs/phase8/phase8_six_factor_ranking_recent5_2020_2025.csv`

### For Slide 3

- `outputs/phase8/phase8_six_factor_panel.csv`
- `outputs/phase8/phase8_summary.md`

---

## Final Presenter Message

If you want one short closing statement for this section, use this:

> Phase 8 fixed the share-split inconsistency in the data and then ranked and weighted the six factors by how much they move. EPS is the most active factor and share count is the least, and the framework is now clean and ready to add price.

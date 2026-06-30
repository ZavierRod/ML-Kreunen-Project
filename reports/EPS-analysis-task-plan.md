# EPS Analysis Task Plan

## Goal

Build a clean, repeatable analysis that explains how changes in:

- `Revenue per Share (Rev/S)`
- `Net Margin`
- `Share Count`

drive changes in:

- `EPS`

using the Google data in `data/GOOG MS ML 10-Year Actuals/Model.csv` and the methodology shown in `data/GOOG EPS Formulas ML Project/Sheet1.csv`.

The most efficient approach is to do this in **two passes**:

1. Replicate the existing formulas sheet exactly for the known `2015-2020` example.
2. Expand the logic into a clean yearly analysis table that can answer all follow-up questions for `2015-2025`, `2010-2025`, and `2001-2025`.

---

## What Matters In The Source Files

### File 1: `data/GOOG EPS Formulas ML Project/Sheet1.csv`

This file shows the starter methodology.

It uses:

- `Rev ($m)`
- `Net Income`
- `#Shares(m)`
- `Rev/S`
- `NetMargin`
- `∆Rev/Share`
- `∆NetMargin`
- `∆EPS`

Important observation:

- The formulas sheet is using a **simple additive year-over-year decomposition**:
  - `∆EPS = ∆Rev/S + ∆NetMargin`

This is the logic you should first replicate exactly.

### File 2: `data/GOOG MS ML 10-Year Actuals/Model.csv`

For now, only pull these rows from the `Model` tab:

- `Total Gross revenue (GAAP)`
- `Net income, reported`
- `Average diluted shares`

From those rows, you can derive everything else needed for the analysis.

---

## Core Identities

These are the only formulas you need at the start:

```text
Rev/S = Revenue / Shares
Net Margin = Net Income / Revenue
EPS = Net Income / Shares
EPS = (Revenue / Shares) x (Net Income / Revenue)
EPS = Rev/S x Net Margin
```

That last identity is the key.

It lets you analyze EPS through two layers:

1. `Rev/S`
2. `Net Margin`

Then later, since `Rev/S = Revenue / Shares`, you can break `Rev/S` into:

1. `Revenue growth`
2. `Share count change`

That is how you get the full 3-factor decomposition.

---

## Best Workflow

## Phase 1: Recreate The Existing 2015-2020 Example

Do this first before expanding anything.

### Step 1: Build a clean annual table

Create a table with one row per year and these columns:

- `Year`
- `Revenue`
- `Net Income`
- `Average Diluted Shares`
- `Rev/S`
- `Net Margin`
- `EPS`

Use years:

- `2015`
- `2016`
- `2017`
- `2018`
- `2019`
- `2020`

### Step 2: Recalculate the base metrics

For each year:

```text
Rev/S = Revenue / Shares
Net Margin = Net Income / Revenue
EPS = Net Income / Shares
```

### Step 3: Replicate the formulas sheet logic exactly

For each year-over-year period:

```text
∆Rev/S = (Rev/S_t / Rev/S_t-1) - 1
∆NetMargin = (NetMargin_t / NetMargin_t-1) - 1
∆EPS = (EPS_t / EPS_t-1) - 1
```

Then verify that:

```text
∆EPS ≈ ∆Rev/S + ∆NetMargin
```

This replication check is your proof that you understand the methodology correctly.

### Why this step matters

If this first check does not match the formulas sheet, stop and fix that before expanding to longer windows.

---

## Phase 2: Expand The Same 2-Factor Method To Longer Windows

Once the replication works, extend the same setup to:

- `2015-2025`
- `2010-2025`
- `2001-2025`

For each window, produce:

- yearly `Revenue`
- yearly `Net Income`
- yearly `Shares`
- yearly `Rev/S`
- yearly `Net Margin`
- yearly `EPS`
- year-over-year `∆Rev/S`
- year-over-year `∆NetMargin`
- year-over-year `∆EPS`

### Output to create

For each window, create a section or table that shows:

- the year pair, such as `2015-2016`
- contribution from `∆Rev/S`
- contribution from `∆NetMargin`
- resulting `∆EPS`

---

## Phase 3: Build The Full 3-Factor EPS Decomposition

After the 2-factor version is done, move to the more complete model.

Because:

```text
EPS = Revenue x Net Margin / Shares
```

you can decompose EPS change into:

- `Revenue growth`
- `Net Margin change`
- `Share count change`

### Recommended approach

Use the 3-factor model for the deeper business questions, because it matches the wording of the task better than the 2-factor version.

### Practical implementation

For each year-over-year period, calculate growth rates for:

```text
Revenue change % = (Revenue_t / Revenue_t-1) - 1
Margin change % = (NetMargin_t / NetMargin_t-1) - 1
Shares change % = (Shares_t / Shares_t-1) - 1
EPS change % = (EPS_t / EPS_t-1) - 1
```

### Easy-to-understand decomposition

Use this structure:

```text
Rev/S contribution = Revenue growth contribution + Share count contribution
EPS contribution = Revenue contribution + Margin contribution + Share count contribution
```

For presentation, define share count impact so it reads intuitively:

- falling shares = positive EPS contribution
- rising shares = negative EPS contribution

One clean way to express that is:

```text
Share count contribution = -((Shares_t / Shares_t-1) - 1)
```

### Important note

The exact math will not always sum perfectly with a simple additive method because multiplicative growth creates interaction effects.

To keep the output easy to understand:

- use the simple additive approach for replication with the formulas sheet
- use a clearly labeled 3-factor decomposition for the business questions

If needed, include a small note saying:

> Minor differences may occur due to interaction effects when multiple drivers change at the same time.

---

## Phase 4: Answer The Business Questions

Once the tables are built, the rest becomes a ranking and filtering exercise.

### 1. Replication & Expansion Questions

For each time window:

- show all year-over-year periods
- show `∆Rev/S`
- show `∆NetMargin`
- show `∆EPS`
- explain whether `Rev/S` or `Net Margin` was the larger driver in each period

### 2. Year-Over-Year Decomposition

For every year pair:

- compute contribution from `Revenue`
- compute contribution from `Net Margin`
- compute contribution from `Share count`
- rank all 3 factors by absolute magnitude
- flag the single largest driver
- label it as `positive` or `negative`

### 3. Five-Year Rolling Analysis

Focus on `2020-2025`.

For those year-over-year periods:

- identify the factor that was most consistently positive
- identify the factor with the highest volatility
- identify any years where factors offset each other

Good ways to measure this:

- `consistency`: number of positive contributions
- `volatility`: standard deviation of contribution values
- `offsetting years`: years where one major driver was positive and another was negative

### 4. Correlation & Relationship Questions

Create small supporting calculations:

- correlation between `Revenue growth` and `Net Margin change`
- count of years where `Net Margin` fell but `EPS` still rose
- compare whether buyback-driven EPS lift aligned more with `Revenue growth` or `Net Margin`

Suggested checks:

- `Corr(Revenue growth, Margin change)`
- filter where `Margin change < 0` and `EPS change > 0`
- filter where `Share count change < 0` and compare correlation of share benefit with:
  - `Revenue growth`
  - `Margin change`

---

## The One Important Data Issue You Must Handle

Before trusting the long-history results, check share count consistency across the full dataset.

### Why this matters

The annual `Average diluted shares` series appears to jump sharply around `2014`, which is likely due to a stock split or share-basis change.

That means:

- `2015-2025` is relatively straightforward
- `2010-2025` is still manageable
- `2001-2025` may be misleading unless pre-split shares are normalized

### What to do

Before finalizing the `2001-2025` window:

1. confirm whether pre-2014 shares are split-adjusted
2. if they are not, normalize them to the same basis as post-2014 shares
3. only then calculate long-run `Rev/S` and `EPS` comparisons

If you skip this step, the `2001-2025` output may be directionally wrong.

---

## Most Efficient Build Order

If you want the fastest path with the least confusion, do the work in this exact order:

1. Pull only the 3 source rows from the `Model` tab.
2. Build the clean annual table for `2015-2020`.
3. Replicate the formulas sheet exactly.
4. Extend the same table through `2025`.
5. Expand backward to `2010`.
6. Review share-count consistency before going back to `2001`.
7. Build the 3-factor decomposition.
8. Rank contributions by year.
9. Answer the rolling 5-year and correlation questions.
10. Summarize findings in plain English.

This avoids spending time on advanced questions before validating the base math.

---

## Recommended Deliverables

By the end, you should have:

### Deliverable 1: Clean annual driver table

One table with:

- `Year`
- `Revenue`
- `Net Income`
- `Shares`
- `Rev/S`
- `Net Margin`
- `EPS`

### Deliverable 2: 2-factor replication table

One table showing:

- `Year-to-Year`
- `∆Rev/S`
- `∆NetMargin`
- `∆EPS`

### Deliverable 3: 3-factor decomposition table

One table showing:

- `Year-to-Year`
- `Revenue contribution`
- `Margin contribution`
- `Share count contribution`
- `Total EPS change`
- `Largest driver`
- `Direction`

### Deliverable 4: Insight summary

A short write-up answering:

- what usually drives EPS most
- when drivers offset each other
- whether buybacks or margin tend to amplify revenue better
- whether revenue growth can overcome margin pressure

---

## Simple Interpretation Rules

Use these so the final write-up stays clear.

- If `Rev/S` rises, that helps EPS.
- If `Net Margin` rises, that helps EPS.
- If shares fall, that helps EPS.
- If shares rise, that hurts EPS.
- A large positive `Revenue` effect with a negative `Margin` effect suggests scale without efficiency.
- A large positive `Margin` effect with weaker `Revenue` growth suggests profitability improvement.
- A large positive `Share count` effect usually points to buybacks helping EPS growth.

---

## What Not To Do

Avoid these mistakes:

- do not start with all 503 rows from the model
- do not mix quarterly and annual values in the same analysis
- do not assume pre-2014 shares are directly comparable without checking
- do not jump into correlation work before validating the base decomposition
- do not use a more advanced method until the formulas sheet has been replicated

---

## Monday Game Plan

If you want a practical way to start quickly on Monday, do this:

### First hour

1. Pull the 3 annual rows from the `Model` tab.
2. Rebuild the `2015-2020` example.
3. Confirm the formulas sheet math ties out.

### Second hour

1. Extend the annual table to `2025`.
2. Build the 2-factor output.
3. Build the 3-factor output.

### Third hour

1. Expand backward to `2010`.
2. Check the pre-2014 share-count issue.
3. Decide whether `2001-2025` can be used as-is or must be normalized first.

### Final step

Write a short summary with:

- biggest EPS driver by year
- most consistent positive factor
- most volatile factor
- years where drivers offset each other

---

## Bottom Line

This task is very manageable if you keep it structured.

The easiest successful path is:

- first replicate the exact formulas sheet
- then expand the same logic to longer windows
- then split `Rev/S` into `Revenue` and `Shares`
- then answer the ranking, rolling, and correlation questions

The only real technical risk is the share-count basis change in the older history.

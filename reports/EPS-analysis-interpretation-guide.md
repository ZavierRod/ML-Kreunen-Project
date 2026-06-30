# EPS Analysis Interpretation Guide

## Why This File Exists

This guide explains, in plain English, what the outputs mean, how they connect to each other, and how the final answers were produced.

If you have been looking at the CSVs and thinking:

- what exactly am I supposed to learn from these numbers?
- why are there multiple phases?
- which file answers which question?
- what does a positive or negative contribution actually mean?

this file is meant to answer that.

## The Big Picture

The project is trying to explain how `EPS` changes over time.

At the highest level:

```text
EPS = Net Income / Shares
```

But the project breaks EPS into more useful business drivers.

First:

```text
EPS = Rev/S x Net Margin
```

where:

- `Rev/S` = Revenue per Share = `Revenue / Shares`
- `Net Margin` = `Net Income / Revenue`

Then, for deeper analysis:

```text
EPS = Revenue x Net Margin / Shares
```

That means EPS can be understood through 3 business drivers:

- `Revenue`
- `Net Margin`
- `Share Count`

So the full story of the project is:

1. Replicate the original formula sheet exactly.
2. Expand that same logic across longer time windows.
3. Build a better 3-factor model that ties out exactly.
4. Use that model to answer the business questions.

## What Each Phase Was Doing

### Phase 1: Replication

Main goal:

- prove that the original `Sheet1.csv` logic was understood correctly

Main files:

- `outputs/phase1/phase1_eps_annual_table_2015_2020.csv`
- `outputs/phase1/phase1_eps_replication_check_2015_2020.csv`
- `outputs/phase1/phase1_eps_replication_summary_2015_2020.md`

What happened here:

- The project rebuilt the annual data for `2015-2020`.
- It recalculated `Rev/S`, `Net Margin`, and `EPS`.
- It checked whether those values reproduce the same outputs shown in `data/GOOG EPS Formulas ML Project/Sheet1.csv`.

What you should understand from Phase 1:

- the replication worked
- the original sheet was matched exactly
- the formula sheet is using a `base-year horizon` method, not adjacent year-over-year changes
- the sheet's `∆EPS` is an `additive approximation`, not the exact true EPS CAGR

This is very important.

The formula sheet is effectively saying:

```text
∆EPS ≈ ∆Rev/Share + ∆NetMargin
```

That is close, but not exact, because EPS is multiplicative, not purely additive.

### Phase 2: Expansion

Main goal:

- extend the same sheet-style logic to longer ranges

Main files:

- `outputs/phase2/phase2_eps_annual_tables.csv`
- `outputs/phase2/phase2_eps_horizon_expansion.csv`
- `outputs/phase2/phase2_eps_validation_results.csv`
- `outputs/phase2/phase2_eps_summary.md`

What happened here:

- The same methodology from the formula sheet was expanded to:
- `2015-2025`
- `2010-2025`
- `2001-2025`

What you should understand from Phase 2:

- this phase is still following the original sheet logic
- it is still horizon-based from a base year
- it is not yet the final business-answer model

This phase answers:

- can the original methodology be scaled up?

Answer:

- yes, mechanically it works

But it also reveals something important:

- the gap between the sheet-style additive approximation and true EPS growth gets bigger in long windows

That is why the project needed a better model in Phase 3.

### Phase 3: Exact 3-Factor Decomposition

Main goal:

- build a more rigorous model that explains EPS changes exactly

Main files:

- `outputs/phase3/phase3_eps_annual_tables.csv`
- `outputs/phase3/phase3_eps_three_factor_decomposition.csv`
- `outputs/phase3/phase3_eps_validation_results.csv`
- `outputs/phase3/phase3_eps_summary.md`

What happened here:

- Instead of only splitting EPS into `Rev/S` and `Net Margin`, this phase split EPS into:
- `Revenue`
- `Net Margin`
- `Share Count`

Why this matters:

- this is closer to how a finance or business audience would think about EPS
- it separates operating growth from profitability and buybacks/share dilution

Most important result:

- the Phase 3 decomposition ties out exactly

That means the contributions truly add back to total EPS change.

This is the phase that makes the final answers trustworthy.

### Phase 4: Final Answers

Main goal:

- turn the exact Phase 3 outputs into direct answers to the assignment questions

Main files:

- `outputs/phase4/phase4_eps_two_factor_yoy.csv`
- `outputs/phase4/phase4_eps_year_over_year_analysis.csv`
- `outputs/phase4/phase4_eps_validation_results.csv`
- `outputs/phase4/phase4_eps_business_answers.md`
- `reports/EPS-analysis-question-answers.md`

What happened here:

- the outputs were ranked
- the largest drivers were labeled
- rolling 5-year analysis was calculated
- correlations and relationship checks were calculated
- the narrative answers were written

This is the phase that directly answers the assignment.

## The Most Important Concept: There Are 2 Different Methods In This Project

This is probably the single most important thing to understand.

### Method 1: Sheet-style horizon method

Used in:

- Phase 1
- Phase 2

Characteristics:

- starts from a base year
- compares that base year to future years
- annualizes the result over the horizon length
- uses the original formula-sheet style

Example:

- `2015-2017` in Phase 2 means a 2-year horizon from 2015 to 2017
- it does not mean the adjacent yearly move from 2016 to 2017

### Method 2: Exact year-over-year decomposition

Used in:

- Phase 3
- Phase 4

Characteristics:

- compares adjacent periods
- `2016-2017` means exactly 2016 to 2017
- uses exact decomposition logic
- is more appropriate for business interpretation

So when numbers do not match across all files, that does not automatically mean something is wrong.

Often it means:

- the files are answering different versions of the question

## Which Files Matter Most For Interpretation

If you want the simplest reading order, use this:

1. `outputs/phase1/phase1_eps_replication_summary_2015_2020.md`
2. `outputs/phase2/phase2_eps_summary.md`
3. `outputs/phase3/phase3_eps_summary.md`
4. `outputs/phase4/phase4_eps_business_answers.md`
5. `reports/EPS-analysis-question-answers.md`

If you want the actual numbers behind the answers, use this:

1. `outputs/phase4/phase4_eps_two_factor_yoy.csv`
2. `outputs/phase4/phase4_eps_year_over_year_analysis.csv`

## How To Read The Main CSVs

### 1. `outputs/phase1/phase1_eps_replication_check_2015_2020.csv`

This file is a proof file.

Key columns:

- `delta_rev_per_share_calculated`: what your code calculated
- `delta_rev_per_share_sheet`: what the formula sheet says
- `delta_net_margin_calculated`: what your code calculated
- `delta_net_margin_sheet`: what the formula sheet says
- `delta_eps_actual_cagr`: the true EPS growth
- `delta_eps_sheet_logic_calculated`: the additive approximation
- `delta_eps_sheet`: the formula sheet value
- `additive_gap`: the difference between true EPS CAGR and the additive approximation

How to interpret it:

- if the calculated columns match the sheet columns, replication succeeded
- if `additive_gap` is not zero, that shows the additive formula is only an approximation

What this file tells you:

- the project understood the original spreadsheet correctly

### 2. `outputs/phase2/phase2_eps_horizon_expansion.csv`

This file extends the same idea over more years.

Key columns:

- `window_label`: which range the row belongs to
- `base_year`: starting year
- `target_year`: ending year
- `horizon_years`: number of years in the horizon
- `delta_rev_per_share`
- `delta_net_margin`
- `delta_eps_sheet_logic`
- `delta_eps_actual_cagr`
- `additive_gap`

How to interpret it:

- this file shows how the original sheet logic behaves in longer windows
- it is useful for replication and expansion
- it is not the strongest file for final business interpretation

What this file tells you:

- the original methodology can be extended
- but its approximation weakness becomes more noticeable over longer histories

### 3. `outputs/phase3/phase3_eps_three_factor_decomposition.csv`

This is one of the most important files in the whole project.

Key columns:

- `revenue_growth`
- `net_margin_growth`
- `share_count_growth`
- `eps_growth`
- `revenue_log_contribution`
- `net_margin_log_contribution`
- `share_count_log_contribution`
- `eps_log_change`
- `tie_out_gap`
- `largest_driver`
- `largest_driver_direction`

How to interpret it:

- each row is one adjacent year-to-year period
- positive contribution means that factor helped EPS
- negative contribution means that factor hurt EPS
- the larger the absolute value, the stronger the effect
- `tie_out_gap` being near zero means the decomposition works exactly

Important note:

- `share_count_log_contribution` is defined so that lower share count helps EPS
- so if shares fall because of buybacks, the contribution becomes positive

What this file tells you:

- what actually drove EPS each year

### 4. `outputs/phase4/phase4_eps_two_factor_yoy.csv`

This file is a cleaner 2-factor year-over-year bridge.

Key columns:

- `delta_rev_per_share_growth`
- `delta_net_margin_growth`
- `delta_eps_growth`
- `rev_per_share_log_contribution`
- `net_margin_log_contribution`
- `eps_log_change`
- `two_factor_tie_out_gap`
- `dominant_two_factor`

How to interpret it:

- this is the year-over-year version of the 2-factor view
- it answers: was EPS mainly driven by `Rev/S` or by `Net Margin` in each period?

Example:

- in `2016-2017`, `rev_per_share_log_contribution = 0.2022`
- `net_margin_log_contribution = -0.6361`
- `eps_log_change = -0.4339`

Meaning:

- revenue per share helped EPS
- margin hurt EPS much more strongly
- margin was the dominant driver
- overall EPS fell

### 5. `outputs/phase4/phase4_eps_year_over_year_analysis.csv`

This is the most important answer file.

It contains the full 3-factor interpretation plus rankings.

Key columns:

- `revenue_log_contribution`
- `net_margin_log_contribution`
- `share_count_log_contribution`
- `largest_driver`
- `largest_driver_direction`
- `rank_1_factor`
- `rank_2_factor`
- `rank_3_factor`
- `has_offsetting_factors`
- `eps_direction`

How to interpret it:

- this file tells you which factor mattered most in each period
- it also tells you if factors were moving in opposite directions

Example:

- in `2021-2022`
- revenue contribution is positive
- net margin contribution is negative and larger in magnitude
- share count contribution is positive
- `has_offsetting_factors = yes`
- `largest_driver = net_margin`
- `eps_direction = negative`

Meaning:

- revenue and buybacks helped
- margin deterioration hurt more than they helped
- EPS still fell overall

That is exactly the kind of logic the assignment is asking you to discuss.

## How The Final Answers Were Derived

This section explains how to connect the output files to the actual assignment questions.

### Question Area 1: Replication and expansion

Answered mainly by:

- `outputs/phase1/phase1_eps_replication_summary_2015_2020.md`
- `outputs/phase2/phase2_eps_summary.md`
- `outputs/phase4/phase4_eps_two_factor_yoy.csv`

Logic:

- Phase 1 proved the original sheet was replicated correctly
- Phase 2 extended the same methodology to longer windows
- Phase 4 then gave a year-over-year two-factor interpretation

What the answer is:

- yes, the formula-sheet logic was replicated successfully
- yes, it was expanded to longer ranges
- but the stronger business interpretation comes from the year-over-year exact bridge, not just the old sheet logic

### Question Area 2: Year-over-year decomposition

Answered mainly by:

- `outputs/phase4/phase4_eps_year_over_year_analysis.csv`
- `reports/EPS-analysis-question-answers.md`

Logic:

- for each period, measure the contributions from revenue, margin, and shares
- rank them by absolute size
- identify the largest one and its direction

What the answer is:

- the largest full-history swing is `share_count` in `2013-2014`
- but that is likely distorted by a share-basis break
- excluding that break, the largest swing is `revenue` in `2001-2002`

### Question Area 3: Five-year rolling analysis

Answered mainly by:

- `outputs/phase4/phase4_eps_business_answers.md`
- `reports/EPS-analysis-question-answers.md`

Logic:

- focus on the last five adjacent periods
- count how often each factor is positive
- measure volatility using standard deviation
- check whether factors offset each other

What the answer is:

- `revenue` was the most consistently positive contributor
- `net_margin` was the most volatile factor
- the clearest offsetting year was `2021-2022`

How to understand that:

- revenue kept helping
- margin was the least stable driver
- even when other things were going well, a large margin decline could still reverse the total EPS result

### Question Area 4: Correlation and relationships

Answered mainly by:

- `outputs/phase4/phase4_eps_business_answers.md`
- `reports/EPS-analysis-question-answers.md`

Logic:

- calculate correlation between revenue growth and margin change
- count periods where margin fell but EPS still rose
- compare buyback-related share benefits with revenue and margin patterns

What the answer is:

- revenue growth and margin change have a moderate positive correlation
- EPS still rose in 6 periods even though margin fell
- in those cases, revenue growth was strong enough to overcome the drag
- when share count fell, that EPS boost aligned more with revenue than margin

## How To Read Positive and Negative Contributions

This is a simple rule set you can always use.

### Revenue

- positive = revenue growth helped EPS
- negative = revenue decline hurt EPS

### Net Margin

- positive = profitability improved and helped EPS
- negative = profitability weakened and hurt EPS

### Share Count

- positive = lower share count helped EPS
- negative = rising share count diluted EPS

## The 2013-2014 Caveat

This is the biggest warning in the whole project.

The outputs repeatedly note a `share-basis break around 2014`.

What that means:

- the share count series may not be fully comparable before and after that point
- that can create an artificial-looking jump in share-related results
- the `2013-2014` share count effect may reflect a split or basis shift rather than true business performance

How you should talk about it:

- do not present `2013-2014` as a clean business conclusion
- treat it as a data-series caveat
- explain that the long-history results are directionally useful, but share-related findings need caution

The cleanest interpretation ranges are:

- `2015-2025`: strongest and cleanest
- `2010-2025`: usable with care
- `2001-2025`: useful for direction, but must be caveated on share-count interpretation

## A Simple Way To Explain The Whole Project Out Loud

If you need to explain this to someone else, this is a good version:

```text
First, I reproduced the original spreadsheet exactly so I could prove I understood its logic.
Then I extended that same approach across longer time windows.
After that, I built a better three-factor decomposition that explains EPS exactly through revenue, margin, and share count.
Finally, I used that exact decomposition to answer the business questions about the biggest drivers, the most consistent drivers, the most volatile drivers, and the relationship between revenue, margin, and buybacks.
```

## A Simple Way To Explain The Answers

If you need a short summary of the results, this is the cleanest version:

```text
The original formula sheet was replicated successfully.
Revenue was the most consistently positive driver of EPS in the recent five-year period.
Net margin was the most volatile driver.
The largest full-history share-count effect appears in 2013-2014, but that should be treated cautiously because the share series likely has a basis break there.
Excluding that break, revenue is the largest positive long-history driver.
```

## How Everything Ties Together

Here is the full chain from start to finish.

### Step 1

Start with raw company data:

- revenue
- net income
- diluted shares

### Step 2

Convert the raw data into:

- `Rev/S`
- `Net Margin`
- `EPS`

### Step 3

Replicate the original spreadsheet to confirm the math

### Step 4

Expand that same spreadsheet logic to longer windows

### Step 5

Replace the approximation with an exact year-over-year decomposition

### Step 6

Rank the drivers and summarize the trends

### Step 7

Write the business answers using those ranked, validated outputs

That is how the project moves from:

- raw data

to:

- validated model outputs

to:

- final written conclusions

## What You Should Be Most Confident Saying

These are the safest and strongest takeaways.

- The project successfully replicated the original formula sheet.
- The project successfully expanded that methodology to longer windows.
- The exact 3-factor decomposition is the strongest analytical result because it ties out perfectly.
- Revenue is the most consistent recent positive EPS driver.
- Net margin is the most volatile recent EPS driver.
- Share-count conclusions in the long history must be caveated because of the 2014 basis break.

## What File To Open Depending On Your Need

If you want:

- proof replication worked: open `outputs/phase1/phase1_eps_replication_check_2015_2020.csv`
- expanded horizon outputs: open `outputs/phase2/phase2_eps_horizon_expansion.csv`
- exact factor decomposition: open `outputs/phase3/phase3_eps_three_factor_decomposition.csv`
- final year-over-year 2-factor answers: open `outputs/phase4/phase4_eps_two_factor_yoy.csv`
- final year-over-year 3-factor answers: open `outputs/phase4/phase4_eps_year_over_year_analysis.csv`
- plain-English answers: open `reports/EPS-analysis-question-answers.md`
- short high-level overview: open `reports/EPS-analysis-executive-summary.md`

## Final Takeaway

The project is not just a collection of CSVs.

It is a sequence of steps that builds confidence:

1. replicate the original sheet
2. expand the original method
3. improve the method so it becomes exact
4. use that exact method to answer the real business questions

So the best way to understand the outputs is:

- Phase 1 and Phase 2 show that the spreadsheet logic was understood and expanded
- Phase 3 provides the exact analytical engine
- Phase 4 turns that engine into the final answers

If you keep that structure in mind, the whole project becomes much easier to follow.

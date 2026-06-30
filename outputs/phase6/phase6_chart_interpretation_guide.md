# Phase 6 Chart Interpretation Guide

This guide walks through every chart in [notebooks/phase6_rolling_cagr_eda.ipynb](../../notebooks/phase6_rolling_cagr_eda.ipynb) and gives you:

- **What the chart shows** - the mechanics of what's being plotted
- **Key observations** - specific numbers pulled from the Phase 6 data
- **Slide-ready takeaways** - one-liners you can drop straight into a deck for Connor

Use this alongside [phase6_eps_rolling_five_year_summary.md](phase6_eps_rolling_five_year_summary.md) (the factual summary of the CSV).

---

## Setup context you'll need on slide 1

- **Data window:** rolling 5-year slots, shifted 1 year at a time, from `2001-2006` through `2020-2025` - 20 slots total.
- **Metric per factor:** CAGR = `(end_value / start_value) ** (1/5) - 1`.
- **Factors tracked:** Revenue, Net Income, Shares, Net Margin, Rev/S, EPS.
- **Important caveat to call out early:** slots that straddle the 2013-2014 share-basis break (2009-2014 through 2013-2018) show an artificial ~84% shares CAGR and a corresponding ~-35% Rev/S and EPS CAGR. These are not operational moves - they are an accounting/basis artifact. Every chart below has this fingerprint, so flag it once and then move on.

---

## Chart 1 - Distribution of rolling 5-year CAGR (histograms, 2x3 grid)

### What it shows

For each of the six factors, a histogram of its CAGR across the 20 rolling slots, with a **dashed black line at the mean** and a **dotted grey line at the median**.

### Key observations

| Factor | Mean | Median | Shape |
|---|---|---|---|
| Revenue | 36.7% | 20.6% | Highly right-skewed; bulk clusters in 15-25%, long tail out to 160%+ (the 2001-era slots) |
| Net Income | 44.6% | 24.3% | Same right-skew as revenue, reflecting the same early hyper-growth era |
| Shares | 22.2% | 1.7% | Bimodal: a stack near 0-10% plus an isolated cluster near 84% (the 5 slots that cross the 2013-2014 share basis break) |
| Net Margin | 4.1% | 1.8% | Roughly symmetric around 0%, ranges from about -12% to +29%. Most volatile factor in percentage-point terms |
| Rev/S | 20.6% | 19.9% | Mean almost equals median (tight, symmetric distribution in the "clean" slots) with a separate negative cluster from the basis-break slots |
| EPS | 28.7% | 23.8% | Wide spread from -44% to +205%, reflecting every shock revenue, margin, or shares has ever thrown at it |

### Slide-ready takeaways

- "Across every 5-year window in the history, Google's **median** 5-year Revenue CAGR is **~21%** and median EPS CAGR is **~24%**. The means are much higher because the 2001-era slots still carry 100%+ growth."
- "Mean-vs-median gap is the story: the bigger the gap, the more 'hyper-growth legacy' is in that factor. Use the **median** as the representative Google number going forward."
- "Net Margin CAGR sits around **0%** most of the time - meaning margins are roughly stable on average, with episodic expansions and compressions."

---

## Chart 2 - Rolling 5-year CAGR spread by factor (boxplot with jittered dots)

### What it shows

A single view of the spread of each factor's CAGR. The **box** is the interquartile range, the **horizontal line** is the median, the **diamond** is the mean, and every **coloured dot** is one rolling slot overlaid with horizontal jitter.

### Key observations

- **Revenue and Rev/S boxes sit at roughly the same height (~20% median)** - this is the closest thing to a "steady-state Google growth rate" on the slide.
- **Net Margin is the tightest box** - most slots are within a few percentage points of zero change in margin. The few outliers above +20% are the 2001-era expansions.
- **Shares has a tiny IQR near 0% with a huge cluster of outliers near +84%** - visually makes the basis-break artifact obvious.
- **EPS has the widest box of any factor** - confirming that EPS volatility is the compounded result of the other five factors moving together.

### Slide-ready takeaways

- "EPS is the **most volatile** of the six factors. That is expected - EPS is a product of three other volatile inputs (revenue, margin, shares)."
- "The **narrow Rev/S box** is notable: in 13 of 20 slots, revenue-per-share CAGR landed within a ~5-point band around 20%. That's the business's 'home base' once you strip out the share-basis noise."
- "The jittered dots make the 2013-2014 basis break look like a literal split in the data - use this chart to introduce and then dismiss the artifact."

---

## Chart 3 - Rolling 5-year CAGR by factor (combined time series)

### What it shows

Every factor's CAGR plotted on the same axis against the slot's **end year**. Each point answers: "as of this calendar year, what was the annualized growth over the prior 5 years?"

### Key observations (reading left to right)

- **2006-2008:** All factors elevated; Revenue CAGR at 160%+, EPS CAGR above 200% - the Google IPO / early-ads era.
- **2009-2013:** Orderly convergence; Revenue, Net Income, Rev/S, and EPS all settle into the **20-30% band**. Net Margin hovers near 0%.
- **2014-2018 (the "ditch"):** Shares CAGR spikes to ~84%, Rev/S and EPS CAGR collapse to **-35% to -44%**. This is the share-basis break propagating through every slot that contains it.
- **2019-2025 (the "modern era"):** Shares CAGR turns slightly **negative (~-2%)** - buybacks. Net Margin CAGR turns **positive (+6% to +13%)** - margin expansion. Net result: EPS CAGR recovers to **~27-38%**, higher than Revenue CAGR (~17-23%).

### Slide-ready takeaways

- "Strip out the basis-break slots and Google's 5-year EPS growth rate has **reaccelerated from ~19% (2015-2020) to ~30% (2020-2025)**."
- "The recent reacceleration is **not revenue-led** - Revenue CAGR is actually lower now than in the 2015-2020 slot. It is driven by **margin expansion and buybacks**."
- "This chart is the headline for your 'where are we now vs history' slide."

---

## Chart 4 - Rolling 5-year CAGR, one panel per factor (small multiples)

### What it shows

Same time series as Chart 3, but split into **six panels** so each factor gets its own y-axis. Each curve is filled under the zero line so direction is visible at a glance.

### Key observations per panel

- **Revenue CAGR:** monotone decay from 160% to ~17%. Clean "maturation curve."
- **Net Income CAGR:** same decay shape, but noisier - margin swings amplify the move.
- **Shares CAGR:** flat near 0-10% except the obvious 2014-2018 plateau at ~84%. Crucial chart for explaining the basis break.
- **Net Margin CAGR:** saw-tooth around zero. Small absolute moves but the direction flips often. Recent trend (2020-2025) is clearly positive (+6% to +13%).
- **Rev/S CAGR:** tracks Revenue closely except during the basis-break slots, where it inverts. Recent slots are ~20%.
- **EPS CAGR:** the compound result - same ditch shape during basis-break years, strong recovery afterward.

### Slide-ready takeaways

- "Use the **Revenue panel alone** to tell the maturation story - it's a textbook curve."
- "Put the **Shares panel next to the EPS panel** side-by-side - the ditch lines up perfectly, visually proving the basis break is not operational."
- "The **Net Margin panel** is the most underappreciated of the six: it shows a clear regime change after 2019 - margins have been expanding for four consecutive rolling windows."

---

## Chart 5 - Slot-over-slot change in rolling 5-year CAGR (inflection view)

### What it shows

The **first difference** of each factor's CAGR series. The y-axis is in **percentage points** (not percent), because it measures how much CAGR changed vs the previous slot. Think of it as the second derivative of growth - a big spike means "something structural changed between adjacent windows."

### Key observations

- **2007-2008:** Giant negative move across Revenue / Net Income / Rev/S / EPS (~-50 to -130 percentage points). That is the early 2000s hyper-growth falling out of the back of the window.
- **2014:** Shares CAGR jumps by **+80 percentage points**; Rev/S and EPS CAGR drop by ~-55 percentage points. This is the share basis break entering the window.
- **2019:** Shares CAGR falls by **-84 percentage points** (back to normal) and Rev/S / EPS recover by **+50 percentage points**. Same basis break exiting the window.
- **2020-2025:** All factors are hugging the zero line - slot-over-slot CAGR changes are within ~5 percentage points. **Regime of low volatility.**

### Slide-ready takeaways

- "The two big spikes (2014 and 2019) are **the same event** entering and leaving the rolling window - not two separate events."
- "For the last 5 rolling slots, all factor CAGRs are moving by **less than 5 percentage points per slot**. Growth has become **structurally stable** - good setup for forecasting."
- "This is your 'stability vs turbulence' chart - useful if Connor asks 'how reliable is the current growth rate?'"

---

## Cross-chart: the one-slide story for Connor

If you had to distill the entire Phase 6 EDA into one slide, it would say:

1. **History.** Across 20 rolling 5-year windows, Google's median annualized growth is **~21% revenue** and **~24% EPS** (Chart 1 / Chart 2).
2. **Shape.** Growth decays smoothly from 160%+ in the mid-2000s to the high-teens today - a classic maturation curve (Chart 3 / Chart 4).
3. **Artifact to flag.** Slots from 2014 to 2018 include the 2013-2014 class-C share-basis break and should not be interpreted as operational collapse (Chart 4 shares panel, Chart 5 spikes).
4. **Modern era.** The last 5 clean slots (2019-2025 end years) show revenue CAGR of **17-23%**, margin expansion of **+1% to +13%**, buybacks of **~-2%**, and EPS CAGR of **~19% to ~38%** - i.e. **EPS growth is outpacing revenue growth thanks to margin + capital return, not top-line acceleration**.
5. **Stability.** Slot-over-slot CAGR changes are inside **5 percentage points** for every factor in the recent period - the fundamentals have been unusually quiet (Chart 5).

Drop that structure into the deck and the charts become the evidence.

---

## Caveats to keep on the appendix slide

- CAGR is sensitive to endpoints; any single weak or strong year bleeds into 5 slots.
- Net Margin CAGR is a CAGR *of a ratio*, not a CAGR of a dollar amount - interpret it as "how fast is the margin ratio changing" rather than "how fast is profit changing."
- Phase 6 is intentionally CAGR-only. For the **mathematical tie-out** (log contributions that sum exactly to EPS change), use Phase 5's slot view.

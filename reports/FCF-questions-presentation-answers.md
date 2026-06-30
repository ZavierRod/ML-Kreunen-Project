# FCF Factor Questions - Presentation Answers (Phase 7)

A slide-ready, plain-English answer to each question, focused on **Free Cash Flow**.

The questions are the same template as the EPS round, just pointed at the cash-flow factors:

- "EPS" becomes **FCF per share (FCF/S)**
- "Net Margin" becomes **FCF Margin** (= Free Cash Flow / Revenue)
- "Rev/S" (revenue per share) and "Share Count" stay the same

The ask was: take `∆Rev/S` and `∆FCF Margin`, combine them the multiplicative (additive-in-logs) way
to get `∆FCF`, then with all six factors (the 3 EPS factors + the 3 FCF factors) **rank them, weigh
them**, and answer the question battery **first for just the 3 FCF factors (Part A), then for all 6
together (Part B)**.

---

## How To Read The Numbers (one setup slide)

We break FCF per share into business drivers using two identities:

```text
FCF/S = Rev/S x FCF Margin                  (two-factor)
FCF/S = Revenue x FCF Margin / Shares       (three-factor)
```

- **Rev/S** = Revenue per Share. **FCF Margin** = Free Cash Flow / Revenue.
- Each driver gets a **contribution** number. Contributions for a year **add up exactly** to the
  total FCF/S change that year (this is the "multiplicative addition" - they add up in log form).
- Read a contribution like a percentage: `+0.26` pushed FCF/S up ~26%; `-0.29` pulled it down ~29%.
- **Positive = helped FCF. Negative = hurt FCF.** Share count is signed so **buybacks show up positive**.
- A "**weight**" is each factor's share of the total movement, ignoring direction
  (`|factor| / sum of all |factors|`); the weights for a year add to 100%.
- All figures are validated to tie out exactly.

> Recurring caveat: the **2013-2014** period has a share-count data break (the diluted share basis
> jumps), so that one year's share-count number is an artifact, not a real event. Flag it.

---

# PART A - The 3 FCF Factors (Rev/S, FCF Margin, Share Count)

## 1. Replication & Expansion

**The ask:** apply the formulas-sheet method (Years 1-5, 2015-2020) to FCF and expand to Years 1-10
(2015-2025), Years 1-15 (2010-2025), and Years 1-20 (2001-2025). For each window, show how `∆Rev/S`
and `∆FCF Margin` each contributed to the change in FCF/S, year by year.

**Headline:** Revenue per share is the steady positive engine, but for cash flow the **FCF Margin is a
true co-driver** - it leads the move in about half the recent years, because capex swings cash margins
much more than accounting margins.

### Years 1-10: 2015-2025

| Period | Rev/S contr | FCF Margin contr | FCF/S change | Bigger driver |
| ---    | ---          | ---             | ---          | --- |
| 2015-2016 | +0.1772   | +0.2622         | +0.4394      | FCF Margin |
| 2016-2017 | +0.2022   | -0.2895         | -0.0874      | FCF Margin |
| 2017-2018 | +0.2071   | -0.2570         | -0.0499      | FCF Margin |
| 2018-2019 | +0.1748   | +0.1352         | +0.3100      | Rev/S |
| 2019-2020 | +0.1368   | +0.2043         | +0.3411      | FCF Margin |
| 2020-2021 | +0.3584   | +0.1027         | +0.4610      | Rev/S |
| 2021-2022 | +0.1229   | -0.2037         | -0.0808      | FCF Margin |
| 2022-2023 | +0.1171   | +0.0635         | +0.1805      | Rev/S |
| 2023-2024 | +0.1516   | -0.0839         | +0.0677      | Rev/S |
| 2024-2025 | +0.1582   | -0.1337         | +0.0245      | Rev/S |
  
### Years 1-15: 2010-2025 (adds the five earlier pairs)

| Period    | Rev/S contr | FCF Margin contr | FCF/S change | Bigger driver |
| ---       | --- | --- | --- | --- |
| 2010-2011 | +0.2446 | +0.1977 | +0.4423 | Rev/S |
| 2011-2012 | +0.2650 | -0.0986 | +0.1664 | Rev/S |
| 2012-2013 | +0.0818 | -0.2259 | -0.1440 | FCF Margin |
| 2013-2014 | -2.8214 | -0.1492 | -2.9706 | Rev/S (data break) |
| 2014-2015 | +0.1039 | +0.1949 | +0.2988 | FCF Margin |
| ...then 2015-2025 as above | | | | |

### Years 1-20: 2001-2025 (adds the earliest pairs)

| Period | Rev/S contribution | FCF Margin contribution | FCF/S change | Bigger driver |
| --- | --- | --- | --- | --- |
| 2001-2002 | +1.4598 | +0.2529 | +1.7127 | Rev/S |
| 2002-2003 | +1.0534 | -0.5884 | +0.4650 | Rev/S |
| 2003-2004 | +0.7163 | +0.3245 | +1.0408 | Rev/S |
| 2004-2005 | +0.5872 | +0.2468 | +0.8340 | Rev/S |
| 2005-2006 | +0.4879 | -0.5125 | -0.0245 | FCF Margin |
| 2006-2007 | +0.4264 | +0.2505 | +0.6770 | Rev/S |
| 2007-2008 | +0.2686 | +0.2154 | +0.4839 | Rev/S |
| 2008-2009 | +0.0757 | +0.3555 | +0.4312 | FCF Margin |
| 2009-2010 | +0.2030 | -0.4010 | -0.1980 | FCF Margin |
| ...then 2010-2025 as above | | | | |

**Talking point:** "Same method as EPS, now on cash. Revenue per share is again the dependable engine,
but unlike EPS - where Rev/S almost always wins - the FCF Margin is genuinely in charge half the time.
That's the capex cycle: building data centers compresses cash margins even when revenue and accounting
profits look fine. Full tables: `outputs/phase7/phase7_fcf_two_factor_yoy.csv`."

## 2. Year-Over-Year Decomposition

**The ask:** how much of each year's FCF/S change came from **revenue growth**, **FCF margin**, and
**share count**? Rank them each year. Which single factor drove the biggest FCF swing, and was it
positive or negative?

**Headline:** Revenue is still the most frequent #1 driver, but FCF Margin takes the lead far more
often than net margin did for EPS, and it flips sign almost yearly.

### Full three-factor decomposition (2001-2025)

| Period | Revenue | FCF Margin | Share Count | Rank 1 | Rank 2 | Rank 3 | Largest driver | Direction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2001-2002 | +1.6264 | +0.2529 | -0.1666 | revenue | fcf_margin | share_count | revenue | positive |
| 2002-2003 | +1.2046 | -0.5884 | -0.1512 | revenue | fcf_margin | share_count | revenue | positive |
| 2003-2004 | +0.7773 | +0.3245 | -0.0610 | revenue | fcf_margin | share_count | revenue | positive |
| 2004-2005 | +0.6548 | +0.2468 | -0.0677 | revenue | fcf_margin | share_count | revenue | positive |
| 2005-2006 | +0.5467 | -0.5125 | -0.0588 | revenue | fcf_margin | share_count | revenue | positive |
| 2006-2007 | +0.4477 | +0.2505 | -0.0213 | revenue | fcf_margin | share_count | revenue | positive |
| 2007-2008 | +0.2727 | +0.2154 | -0.0041 | revenue | fcf_margin | share_count | revenue | positive |
| 2008-2009 | +0.0817 | +0.3555 | -0.0060 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2009-2010 | +0.2149 | -0.4010 | -0.0119 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2010-2011 | +0.2568 | +0.1977 | -0.0122 | revenue | fcf_margin | share_count | revenue | positive |
| 2011-2012 | +0.2804 | -0.0986 | -0.0154 | revenue | fcf_margin | share_count | revenue | positive |
| 2012-2013 | +0.1012 | -0.2259 | -0.0194 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2013-2014 | +0.1729 | -0.1492 | -2.9943 | share_count | revenue | fcf_margin | share_count | negative (data break) |
| 2014-2015 | +0.1277 | +0.1949 | -0.0238 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2015-2016 | +0.1855 | +0.2622 | -0.0083 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2016-2017 | +0.2054 | -0.2895 | -0.0032 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2017-2018 | +0.2104 | -0.2570 | -0.0033 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2018-2019 | +0.1681 | +0.1352 | +0.0067 | revenue | fcf_margin | share_count | revenue | positive |
| 2019-2020 | +0.1202 | +0.2043 | +0.0166 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2020-2021 | +0.3447 | +0.1027 | +0.0137 | revenue | fcf_margin | share_count | revenue | positive |
| 2021-2022 | +0.0933 | -0.2037 | +0.0296 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2022-2023 | +0.0833 | +0.0635 | +0.0338 | revenue | fcf_margin | share_count | revenue | positive |
| 2023-2024 | +0.1299 | -0.0839 | +0.0218 | revenue | fcf_margin | share_count | revenue | positive |
| 2024-2025 | +0.1405 | -0.1337 | +0.0176 | revenue | fcf_margin | share_count | revenue | positive |

### Which single factor drove the biggest FCF swing?

- **Across all 20 years:** the largest single-factor swing is **share count in 2013-2014, and it was
  negative** - but that is the data break, so flag it.
- **Excluding the break:** the biggest swing is **revenue in 2001-2002, positive** (+1.63).
- **In the recent decade (2015-2025):** the biggest single-factor swing is **revenue in 2020-2021,
  positive** (+0.34) - the post-COVID demand surge.

**Talking point:** "Rank the three factors each year: revenue leads most often, but FCF Margin is #1
in roughly half the years - far more than net margin ever led EPS. And FCF Margin flips between
positive and negative almost every year, which is what makes cash flow choppier than earnings."

## 3. Five-Year Rolling Analysis (2020-2025)

**The ask:** over the last five years, which factor was the most consistent positive contributor to
FCF, and which was the most volatile? Did any factors move in opposite directions and offset each other?

**Headline:** Revenue was the steady, always-positive contributor; FCF Margin was both the most
volatile factor AND a net drag over the period - the key difference from the EPS story.

| Factor | Positive years (of 5) | Average contribution | Volatility (std dev) |
| --- | --- | --- | --- |
| Revenue | 5 of 5 | +0.1583 | 0.1069 |
| FCF Margin | 2 of 5 | **-0.0510 (net negative)** | **0.1303 (highest)** |
| Share Count | 5 of 5 | +0.0233 | 0.0083 (lowest) |

- **Most consistent positive contributor:** Revenue (positive every year).
- **Most volatile:** FCF Margin (biggest swings, and the only factor that was negative on average).
- **Offsetting moves:** Yes, and more often than for EPS - in **2021-2022, 2023-2024, and 2024-2025**
  revenue pushed FCF/S up while FCF Margin pulled it down.

**Talking point:** "Here's the headline contrast with earnings: for EPS, net margin was volatile but
still a net positive over 2020-2025. For cash flow, the margin factor was volatile AND a net drag -
rising capex ate into FCF margin three of the last four years. Revenue is what kept FCF/S growing."

## 4. Correlation & Relationships (FCF)

### 4a. When revenue grew significantly, did FCF Margin expand, contract, or stay independent?

**Headline:** Essentially independent - FCF Margin marches to the capex cycle, not the revenue cycle.

- Correlation between revenue growth and FCF-margin change (2001-2025): **+0.07** (basically none).
  Compare to **+0.52** for net margin - so accounting margins ride revenue, but cash margins do not.
- In the **top-quartile revenue-growth years**, FCF margin expanded in **4** and contracted in **2**.

**Talking point:** "When revenue surged, accounting margins reliably widened (operating leverage). Cash
margins did not - the link is near zero. That tells you FCF margin is driven by the investment cycle
(capex, data centers), not by simply selling more. Weaker operating-leverage signal in cash terms."

### 4b. When FCF Margin contracts, can revenue alone still produce positive FCF growth? How often?

**Headline:** Yes - revenue carried FCF through cash-margin pressure 4 times, and was strong enough
on its own each time.

- FCF margin contracted **yet FCF/S still rose** in **4 years**:
  **2002-2003, 2011-2012, 2023-2024, 2024-2025.**
- In **all 4**, revenue's contribution alone outweighed the combined drag from FCF margin and shares.
- (For comparison, the EPS version of this happened 6 times - revenue rescues earnings a bit more
  often than it rescues cash, because cash-margin drags tend to be deeper.)

**Talking point:** "Four times margins squeezed cash but revenue growth still produced higher FCF per
share - including the two most recent years, 2023-2024 and 2024-2025, where the capex ramp hit FCF
margin but the top line carried it."

### 4c. When share count falls (buybacks), does the FCF lift track revenue or FCF Margin more?

**Headline:** The buyback-driven FCF lift lines up a bit more with revenue than with FCF margin.

- In buyback years, the share-count contribution correlates **-0.58 with revenue** and **-0.47 with FCF
  margin** - revenue is the stronger relationship, but only slightly (much closer than the EPS case,
  where it was -0.58 vs -0.24).

**Talking point:** "As with EPS, buyback timing tracks revenue more than margin. But for cash flow it's
a near tie - FCF margin is almost as connected to the buyback pattern as revenue is."

---

# PART B - All 6 Factors (EPS set + FCF set together)

We now rank and weigh all six contribution series side by side: the EPS trio (Rev/S, Net Margin, Share
Count) and the FCF trio (Rev/S, FCF Margin, Share Count). They are kept as two clean bridges rather than
one fabricated 6-way total, because EPS and FCF are different outputs.

**Headline:** Two of the six factors are literally the same in both metrics; the whole EPS-vs-FCF story
comes down to one factor - net margin vs FCF margin.

### The structural insight (a strong slide)

- **Rev/S contribution is identical** in the EPS and FCF bridges every year (same revenue, same shares).
- **Share-count contribution is identical** too - mean absolute contribution is **0.157 for both**. So
  **buybacks lift EPS and FCF/S by the exact same amount**; neither metric is more buyback-sensitive.
- The **only factor that actually differs is the margin**: Net Margin (EPS) vs FCF Margin (FCF).
- Net-margin and FCF-margin contributions correlate **+0.45** - they move loosely together but
  disagree in direction in **11 of 24 years**. That gap is the entire difference between the earnings
  story and the cash story.

### Ranking & weights - the two margins compared (recent 5 years, weight = share of movement)

| Period    | EPS: Rev| EPS: Net Margin | EPS: Shares | FCF: Rev | FCF: FCF Margin | FCF: Shares |
| ---       | ---     | ---             | ---         | ---      | ---             | ---  |
| 2020-2021 | 53.1%   | 44.8%           | 2.1%        | 74.8%    | 22.3%           | 3.0% |
| 2021-2022 | 20.6%   | 72.9%           | 6.5%        | 28.6%    | 62.4%           | 9.1% |
| 2022-2023 | 34.5%   | 51.5%           | 14.0%       | 46.1%    | 35.2%           | 18.7%|
| 2023-2024 | 39.7%   | 53.6%           | 6.7%        | 55.1%    | 35.6%           | 9.2% |
| 2024-2025 | 47.6%   | 46.5%           | 6.0%        | 48.2%    | 45.8%           | 6.0% |
 - EPS leans on Margin, FCF leans on Revenue

### All-6 direct answers (same questions, combined view)

- **Most consistent positive contributor (both metrics):** Revenue - positive in all 5 recent years for
  EPS and FCF alike.
- **Most volatile (both metrics):** the margin term. Net margin is volatile for EPS but stays net
  positive; FCF margin is even more volatile and turns net negative - so the cash metric is the choppier
  of the two.
- **Offsetting moves:** EPS had one (2021-2022); FCF had three (2021-2022, 2023-2024, 2024-2025) -
  cash flow has more internal tug-of-war because of capex.
- **Revenue rescuing the metric during margin pressure:** revenue carried EPS 6 times and FCF 4 times.
- **Buybacks:** identical effect on both metrics; track revenue slightly more than either margin.
- **Biggest weight shift:** EPS leans more on net margin in 2022-2024 (margin >50% weight), while FCF
  leans more on revenue; the two converge in 2024-2025 as FCF margin recovered.

**Talking point:** "When you put all six factors together, the punchline is simple: revenue and
buybacks hit earnings and cash identically. The reason FCF behaves differently from EPS is one factor -
the margin - because FCF margin absorbs the capex cycle that net margin doesn't see. Earnings lean on
margin; cash leans on revenue."

---

## Suggested Slide Order

1. Title + "How to read the numbers" (the multiplicative-addition setup)
2. Part A intro - the 3 FCF factors
3. Replication: FCF Years 1-10 table
4. Replication: FCF Years 1-15 and 1-20
5. FCF year-over-year decomposition + ranking
6. FCF "biggest single swing" callout
7. FCF five-year rolling: revenue steady vs FCF margin volatile/negative
8. FCF correlations (independence, revenue rescue, buybacks)
9. Part B intro - all 6 factors
10. Structural insight: 2 shared factors, 1 that differs
11. Weights table: the two margins compared
12. Closing takeaways

## Closing Takeaways (a good final slide)

- **Revenue per share is the engine for both EPS and FCF** - always positive, most consistent.
- **The margin factor is the difference-maker.** Net margin makes EPS lumpy; FCF margin makes cash even
  lumpier and was a net drag in 2020-2025 due to capex.
- **Cash margins are independent of revenue (+0.07)**, unlike accounting margins (+0.52) - so FCF has a
  weaker operating-leverage signal.
- **Buybacks help EPS and FCF identically** and track revenue more than margins.
- **Ignore the 2013-2014 share-count data break.**

---

## Where These Numbers Come From

- FCF two-factor (Rev/S + FCF Margin) tables: `outputs/phase7/phase7_fcf_two_factor_yoy.csv`
- FCF three-factor (Revenue + FCF Margin + Share Count), ranks, weights:
  `outputs/phase7/phase7_fcf_three_factor_decomposition.csv`
- All-6 panel and weights: `outputs/phase7/phase7_combined_six_factor_panel.csv`
- Full narrative with the same figures: Phase 7 section of `reports/EPS-analysis-question-answers.md`
- Column-by-column guide to the files: `reports/phase7-FCF-interpretation-guide.md`

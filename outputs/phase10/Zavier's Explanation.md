EV is the company's value with its net cash stripped out, done on a per-share basis: EV = Price - NetCash/share (NetCash/share is the company's total net cash divided by diluted shares). I built this straight on top of Phase 9, reusing the same Price, NetCash, Shares, and FCF numbers, so no new data was pulled. Every "∆" (change) is the same simple year-over-year percent change we've used all along: this year's level divided by last year's, minus 1.

The chain works in three steps:

    EV = Price - NetCash/share, then take ∆EV (how much the cash-free, per-share value moved).

    eff.∆Cash = ∆EV - ∆Price. This is the "effective change in cash," the part of the price move that comes from net cash changing rather than the underlying business.

    C-Return = ∆FCF - eff.∆Cash. This compares how much free cash flow grew against that effective cash change. We call it C-Return so it doesn't get mixed up with the other returns.

Because EV needs a stock price, this history starts in 2004 (when Google went public), which gives us 21 year-over-year periods through 2025. I kept this as its own separate panel instead of folding it into the Phase 9 seven-factor ranking, since eff.∆Cash and C-Return are already changes (differences of percent changes) rather than plain factors.

For the phase10_ev_c_return_panel.csv file, this is the main file. Each row is one year-over-year period with ∆Price, ∆EV, eff.∆Cash, ∆FCF, and C-Return.

For the phase10_ev_levels.csv file, these are the raw yearly building blocks: Price, NetCash per share, EV per share, and FCF, so you can see where the percent changes come from.

For the phase10_ev_c_return_summary_full_2004_2025.csv file, this ranks the four metrics over the full 2004-2025 history by their average size of move.

For the phase10_ev_c_return_summary_recent5_2020_2025.csv file, this is the same but only the most recent 5 years since that's the most relevant.

For the phase10_combined_ranking_full_2004_2025.csv and phase10_combined_ranking_recent5_2020_2025.csv files (presentation tables 15 and 16), these rank the Phase 9 factors and the new EV metrics together by how much each one moves on average. The full-history version uses 2004-2025 so everything is on the same window as EV (Price starts in 2004), which is why those Phase 9 numbers can differ slightly from the Phase 9 2001-2025 tables.

Why there is no weight column: In Phase 9, the weight column shows each factor's share of total movement that year (all weights add to 100%). Tables 15 and 16 do not include that column on purpose. EV, eff.∆Cash, and C-Return are built from Price, NetCash, and FCF, so putting them into the same weight pool would double-count those underlying factors and the 100% share would stop meaning anything. These tables are only for comparing who moves the most (mean_abs), not for splitting movement into shares. FCF also appears only once (as the Phase 9 factor), not twice. The type column marks each row as factor, derived-level (EV), or derived-delta (eff.∆Cash, C-Return) so it is clear which rows are standalone inputs versus derived from other metrics.

Each column name explained:

    mean_abs: the average year-over-year move ignoring direction (a +50% year and a -50% year both count as big). This is what the ranking is sorted by.

    mean: the average move with direction kept, so you can tell whether something mostly grew or swung both ways.

    positive_periods / negative_periods: how many years that metric was up versus down.

What the numbers show: eff.∆Cash is small (only about a 4% average move over the full history), which means net cash barely moves the yearly value, so C-Return ends up tracking free cash flow growth pretty closely. Over 2004-2025, EV moved the most on average (about 42%), and in the recent 5 years EV averaged roughly a 57% move while C-Return averaged about 14%.


BACKTESTING RESEARCH:
    Mixing of frequencies is normal and happens in almost all forecasting cases. It may seem counterintuitive since you would want the factors to be updated just as much as daily price data (since more data is good after all) but that doesn't mean you can't mix and match frequencies. For example, imagine you're guessing how a student's final exam score will change:
    Grades come out every quarter (report cards).
    Daily effort (or daily mood) changes every day.
    You wouldn't say "grades and daily mood must be on the same timeline." You'd say: "When a report card comes out, use it to judge what happens over the next few months."
    Quarterly factors are the report card. Daily prices are what happens in the market after you read it. Just make sure that the timing honesty is matched between the factors, so don't use Q3 numbers in July if Q3 isn't updated until October. So basically: Quarterly factors tell you the state of the business when new data arrives; daily prices tell you what the market did next, they meet at decision dates, so they don't need to share the same update frequency.

Data to gather before backtesting:

1. Filing dates: when each quarter's numbers were actually reported (not quarter-end)
2. Daily prices: full split-adjusted GOOG history since IPO
3. Quarterly fundamentals: Revenue, Net Income, Shares, FCF, Cash, Debt (reported actuals only, no forecasts)
4. Point-in-time master table: one row per filing date with factors + price + forward returns
5. Corporate actions: split dates/ratios so shares and prices stay consistent 
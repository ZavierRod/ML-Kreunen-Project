Phase 11 adds two "effective change" metrics Derek requested. Both build on the same Phase 9 levels (Revenue, Net Margin, Shares) with no new data pull. Every "∆" is still the simple year-over-year percent change: this year's level divided by last year's, minus 1.

The two formulas:

    eff.Shares = (Shares_t-1 / Shares_t - 1) + (Shares_t-1 / Shares_t - 1) * dRevenue
               = (Shares_t-1 / Shares_t - 1) * (1 + dRevenue)

    eff.NetMargin = (Net Margin_t / Net Margin_t-1 - 1) + (Net Margin_t / Net Margin_t-1 - 1) * dRevPerShare
                  = (Net Margin_t / Net Margin_t-1 - 1) * (1 + dRevPerShare)

where dRevenue is the current year's change in total Revenue and dRevPerShare is the current year's change in Revenue per share (Revenue / diluted Shares). The idea is to scale the base share-count or margin move by how much revenue (or revenue per share) grew that same year.

For phase11_effective_panel.csv: each row is one year-over-year period with the building blocks (dRevenue, dShares, shares base change, dNet Margin, dRev/Share) plus the two effective metrics.

For phase11_factor_levels.csv: the yearly inputs used — Revenue, Rev/Share, Net Margin, and Shares.

For phase11_effective_summary_full_2001_2025.csv and the recent-5 version: ranks eff.Shares and eff.NetMargin by average size of move over each window.

For phase11_combined_ranking_full_2001_2025.csv and the recent-5 version (presentation tables 19 and 20): ranks the Phase 9 seven factors and the two effective metrics together by mean_abs. There is no weight column on purpose — eff.Shares and eff.NetMargin are built from Shares, Revenue, Net Margin, and Rev/Share, so putting them into the Phase 9 weight pool would double-count. The type column marks rows as factor or derived-effective.

What the numbers show: eff.Shares is usually much larger than plain Shares because revenue growth amplifies the base share-count move. eff.NetMargin can diverge from plain Net Margin when Rev/Share is moving sharply — margin expansion or compression gets scaled by how fast revenue per share is growing that year.

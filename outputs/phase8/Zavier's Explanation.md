I first normalized the share data for Google's 20-for-1 split by restating the 2001-2013 share counts x20, so the whole history is on a consistent basis. Then I ranked and weighted the six factors (Revenue, Net Margin, EPS, FCF, NetCash, Shares) by how much each one moves year over year, where EPS is the biggest mover and Shares is the smallest.

For the phase8_six_factor_panel.csv file that is the file where we calculate percent change, which is how much each factor moved that year. I also calculated the weight which is the factor's share of the total movement that year (All weights add to 100%)

For the phase8_six_factor_ranking_full_2001_2025.csv file, it is the six factors ranked over the full 24 year history. Each factor's average movement, average weight, and how often it rose or fell.

For the phase8_six_factor_ranking_recent5_2020_2025.csv file, this is the same but only the most recent 5 years since that's the most relevant.


Each column name explained:

    mean_abs_pct_change: is the ranking metric, which is the factor's average year over year move, ignoring direction. 0.97 means it moved 97% on average per year. (absolute so a +50% year and a -50% year both count as big)

    mean_weight: is the factor's average share of total movement across all factors (the per year weights add to 100% then they're averaged)

    mean_pct_change: is the average move with direction kept. You can compare this to mean_abs_pct_change to see if a factor mostly grew or swung both ways

    

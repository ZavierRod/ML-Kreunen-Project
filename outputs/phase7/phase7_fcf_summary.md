# Phase 7 FCF Factor Decomposition Summary

## Testing

All Phase 7 validation checks passed.

Validation file: `outputs/phase7/phase7_fcf_validation_results.csv`

## Method

- Two-factor FCF bridge: `FCF/S = Rev/S x FCF Margin`.
- Three-factor FCF bridge: `FCF/S = Revenue x FCF Margin / Shares`.
- Contributions are exact log contributions, so they tie out to total FCF/S movement.
- Weights are absolute-contribution shares: `|c_i| / sum_j |c_j|` (positive, sum to 100%).
- Positive contribution helps FCF/S; negative hurts it. Share count is signed so buybacks read positive.
- Diluted shares are on a consistent split-adjusted basis across all years (pre-split 2001-2013 restated x20).

## A. The 3 FCF Factors

### Replication & Expansion (two-factor: Rev/S + FCF Margin)

#### Years 1-10: 2015-2025

| Period | Rev/S Contribution | FCF Margin Contribution | FCF/S Change | Dominant 2-Factor Driver |
| --- | --- | --- | --- | --- |
| 2015-2016 | 0.1772 | 0.2622 | 0.4394 | fcf_margin |
| 2016-2017 | 0.2022 | -0.2895 | -0.0874 | fcf_margin |
| 2017-2018 | 0.2071 | -0.2570 | -0.0499 | fcf_margin |
| 2018-2019 | 0.1748 | 0.1352 | 0.3100 | rev_per_share |
| 2019-2020 | 0.1368 | 0.2043 | 0.3411 | fcf_margin |
| 2020-2021 | 0.3584 | 0.1027 | 0.4610 | rev_per_share |
| 2021-2022 | 0.1229 | -0.2037 | -0.0808 | fcf_margin |
| 2022-2023 | 0.1171 | 0.0635 | 0.1805 | rev_per_share |
| 2023-2024 | 0.1516 | -0.0839 | 0.0677 | rev_per_share |
| 2024-2025 | 0.1582 | -0.1337 | 0.0245 | rev_per_share |

#### Years 1-15: 2010-2025

| Period | Rev/S Contribution | FCF Margin Contribution | FCF/S Change | Dominant 2-Factor Driver |
| --- | --- | --- | --- | --- |
| 2010-2011 | 0.2446 | 0.1977 | 0.4423 | rev_per_share |
| 2011-2012 | 0.2650 | -0.0986 | 0.1664 | rev_per_share |
| 2012-2013 | 0.0818 | -0.2259 | -0.1440 | fcf_margin |
| 2013-2014 | 0.1744 | -0.1492 | 0.0252 | rev_per_share |
| 2014-2015 | 0.1039 | 0.1949 | 0.2988 | fcf_margin |
| 2015-2016 | 0.1772 | 0.2622 | 0.4394 | fcf_margin |
| 2016-2017 | 0.2022 | -0.2895 | -0.0874 | fcf_margin |
| 2017-2018 | 0.2071 | -0.2570 | -0.0499 | fcf_margin |
| 2018-2019 | 0.1748 | 0.1352 | 0.3100 | rev_per_share |
| 2019-2020 | 0.1368 | 0.2043 | 0.3411 | fcf_margin |
| 2020-2021 | 0.3584 | 0.1027 | 0.4610 | rev_per_share |
| 2021-2022 | 0.1229 | -0.2037 | -0.0808 | fcf_margin |
| 2022-2023 | 0.1171 | 0.0635 | 0.1805 | rev_per_share |
| 2023-2024 | 0.1516 | -0.0839 | 0.0677 | rev_per_share |
| 2024-2025 | 0.1582 | -0.1337 | 0.0245 | rev_per_share |

#### Years 1-20: 2001-2025

| Period | Rev/S Contribution | FCF Margin Contribution | FCF/S Change | Dominant 2-Factor Driver |
| --- | --- | --- | --- | --- |
| 2001-2002 | 1.4598 | 0.2529 | 1.7127 | rev_per_share |
| 2002-2003 | 1.0534 | -0.5884 | 0.4650 | rev_per_share |
| 2003-2004 | 0.7163 | 0.3245 | 1.0408 | rev_per_share |
| 2004-2005 | 0.5872 | 0.2468 | 0.8340 | rev_per_share |
| 2005-2006 | 0.4879 | -0.5125 | -0.0245 | fcf_margin |
| 2006-2007 | 0.4264 | 0.2505 | 0.6770 | rev_per_share |
| 2007-2008 | 0.2686 | 0.2154 | 0.4839 | rev_per_share |
| 2008-2009 | 0.0757 | 0.3555 | 0.4312 | fcf_margin |
| 2009-2010 | 0.2030 | -0.4010 | -0.1980 | fcf_margin |
| 2010-2011 | 0.2446 | 0.1977 | 0.4423 | rev_per_share |
| 2011-2012 | 0.2650 | -0.0986 | 0.1664 | rev_per_share |
| 2012-2013 | 0.0818 | -0.2259 | -0.1440 | fcf_margin |
| 2013-2014 | 0.1744 | -0.1492 | 0.0252 | rev_per_share |
| 2014-2015 | 0.1039 | 0.1949 | 0.2988 | fcf_margin |
| 2015-2016 | 0.1772 | 0.2622 | 0.4394 | fcf_margin |
| 2016-2017 | 0.2022 | -0.2895 | -0.0874 | fcf_margin |
| 2017-2018 | 0.2071 | -0.2570 | -0.0499 | fcf_margin |
| 2018-2019 | 0.1748 | 0.1352 | 0.3100 | rev_per_share |
| 2019-2020 | 0.1368 | 0.2043 | 0.3411 | fcf_margin |
| 2020-2021 | 0.3584 | 0.1027 | 0.4610 | rev_per_share |
| 2021-2022 | 0.1229 | -0.2037 | -0.0808 | fcf_margin |
| 2022-2023 | 0.1171 | 0.0635 | 0.1805 | rev_per_share |
| 2023-2024 | 0.1516 | -0.0839 | 0.0677 | rev_per_share |
| 2024-2025 | 0.1582 | -0.1337 | 0.0245 | rev_per_share |

### Year-Over-Year Decomposition (three-factor, full 2001-2025)

| Period | Revenue | FCF Margin | Share Count | Rank 1 | Rank 2 | Rank 3 | Largest Driver | Direction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2001-2002 | 1.6264 | 0.2529 | -0.1666 | revenue | fcf_margin | share_count | revenue | positive |
| 2002-2003 | 1.2046 | -0.5884 | -0.1512 | revenue | fcf_margin | share_count | revenue | positive |
| 2003-2004 | 0.7773 | 0.3245 | -0.0610 | revenue | fcf_margin | share_count | revenue | positive |
| 2004-2005 | 0.6548 | 0.2468 | -0.0677 | revenue | fcf_margin | share_count | revenue | positive |
| 2005-2006 | 0.5467 | -0.5125 | -0.0588 | revenue | fcf_margin | share_count | revenue | positive |
| 2006-2007 | 0.4477 | 0.2505 | -0.0213 | revenue | fcf_margin | share_count | revenue | positive |
| 2007-2008 | 0.2727 | 0.2154 | -0.0041 | revenue | fcf_margin | share_count | revenue | positive |
| 2008-2009 | 0.0817 | 0.3555 | -0.0060 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2009-2010 | 0.2149 | -0.4010 | -0.0119 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2010-2011 | 0.2568 | 0.1977 | -0.0122 | revenue | fcf_margin | share_count | revenue | positive |
| 2011-2012 | 0.2804 | -0.0986 | -0.0154 | revenue | fcf_margin | share_count | revenue | positive |
| 2012-2013 | 0.1012 | -0.2259 | -0.0194 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2013-2014 | 0.1729 | -0.1492 | 0.0014 | revenue | fcf_margin | share_count | revenue | positive |
| 2014-2015 | 0.1277 | 0.1949 | -0.0238 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2015-2016 | 0.1855 | 0.2622 | -0.0083 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2016-2017 | 0.2054 | -0.2895 | -0.0032 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2017-2018 | 0.2104 | -0.2570 | -0.0033 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2018-2019 | 0.1681 | 0.1352 | 0.0067 | revenue | fcf_margin | share_count | revenue | positive |
| 2019-2020 | 0.1202 | 0.2043 | 0.0166 | fcf_margin | revenue | share_count | fcf_margin | positive |
| 2020-2021 | 0.3447 | 0.1027 | 0.0137 | revenue | fcf_margin | share_count | revenue | positive |
| 2021-2022 | 0.0933 | -0.2037 | 0.0296 | fcf_margin | revenue | share_count | fcf_margin | negative |
| 2022-2023 | 0.0833 | 0.0635 | 0.0338 | revenue | fcf_margin | share_count | revenue | positive |
| 2023-2024 | 0.1299 | -0.0839 | 0.0218 | revenue | fcf_margin | share_count | revenue | positive |
| 2024-2025 | 0.1405 | -0.1337 | 0.0176 | revenue | fcf_margin | share_count | revenue | positive |

- Largest single-factor FCF/S swing (2001-2025): `revenue` in `2001-2002`, `positive`.

### Five-Year Rolling Analysis (2020-2025)

- Most consistent positive FCF contributor: `revenue`.
- Most volatile factor: `fcf_margin`.
- Offsetting factor moves occurred in: `2021-2022, 2023-2024, 2024-2025`.

| Factor | Positive Periods (of 5) | Mean | Std Dev |
| --- | --- | --- | --- |
| revenue | 5 | 0.1583 | 0.1069 |
| fcf_margin | 2 | -0.0510 | 0.1303 |
| share_count | 5 | 0.0233 | 0.0083 |

### Correlation & Relationships (FCF)

- Revenue growth vs FCF-margin change correlation (2001-2025): `0.0698`.
- In top-quartile revenue-growth years (threshold `0.4498`), FCF margin expanded in `4`, contracted in `2`, flat in `0`.
- FCF margin contracted yet FCF/S still rose in `5` periods; revenue alone outweighed the combined drag in `5` of them.
- For buyback years, share-count contribution correlates `-0.5043` with revenue and `-0.1219` with FCF margin.
  The buyback lift aligns more strongly with revenue than FCF margin.

## B. All 6 Factors (EPS + FCF cross comparison)

- Net-margin vs FCF-margin log-contribution correlation (2001-2025): `0.4531`.
- Mean absolute share-count contribution: EPS `0.0323` vs FCF/S `0.0323`.
  Share count enters both identities identically (same diluted share base), so neither EPS nor FCF/S is structurally more share-count sensitive: the buyback lift is the same for both. The amplification differs only through which margin (net vs FCF) the share effect is paired with.
- Full per-period six-factor weights are in `outputs/phase7/phase7_combined_six_factor_panel.csv`.

## Output Files

- `outputs/phase7/phase7_fcf_annual_tables.csv`
- `outputs/phase7/phase7_fcf_two_factor_yoy.csv`
- `outputs/phase7/phase7_fcf_three_factor_decomposition.csv`
- `outputs/phase7/phase7_combined_six_factor_panel.csv`
- `outputs/phase7/phase7_fcf_validation_results.csv`
- `outputs/phase7/phase7_fcf_factors_sheet_style.csv`
- `outputs/phase7/phase7_fcf_summary.md`

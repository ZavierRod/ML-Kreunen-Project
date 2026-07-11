# Codex Prompt: Build Interactive Factor Ranking & Weighting Explorer

Copy everything below the line into Codex. Work in the repo at the workspace root (`ML-Kreunen-Project`).

---

## Your task

Build a **local, interactive UI** for the GOOG ML factor-ranking project so we can answer live “what-if” questions during review meetings — e.g.:

- “Show weightings and rankings for these **4** factors.”
- “Now make it **6** factors.”
- “Add Price — what changes?”
- “Rank only the Phase 10 EV metrics over 2020–2025.”
- “Compare full history vs recent 5 years side by side.”

The UI must **recompute rankings and weights on the fly** from the underlying level data (not just display pre-baked CSV tables). Precomputed CSVs are for validation only.

Deliver a runnable app plus a short README section at the bottom of this file (or `ui/README.md`) explaining how to start it.

---

## Repo context (read before coding)

This is a Python research repo. Phases 8–11 extend a factor-ranking pipeline for Google (GOOG):

| Phase | What it adds | Weight column? |
| --- | --- | --- |
| **8** | 6 standalone factors | Yes — among selected standalone factors |
| **9** | +Price (7 factors total) | Yes |
| **10** | EV, eff.∆Cash, C-Return (built from Price, NetCash, FCF) | **No** when mixed with parents (double-count risk) |
| **11** | eff.Shares, eff.NetMargin (built from Shares, Revenue, Net Margin, Rev/Share) | **No** when mixed with parents |

**Key existing scripts (source of truth for math):**

- `scripts/phase8_six_factor_ranking.py` — 6-factor weights & ranks
- `scripts/phase9_seven_factor_ranking.py` — 7-factor weights & ranks (+ Yahoo price)
- `scripts/phase10_enterprise_value.py` — EV chain
- `scripts/phase11_effective_shares_margin.py` — effective metrics

**Key data files the UI should load:**

- `outputs/phase9/phase9_factor_levels.csv` — annual levels for all 7 standalone factors
- `outputs/phase9/phase9_seven_factor_panel.csv` — validation reference (per-period pct + weights for all 7)
- `outputs/phase10/phase10_ev_levels.csv` and `outputs/phase10/phase10_ev_c_return_panel.csv`
- `outputs/phase11/phase11_effective_panel.csv`
- `data/GOOG MS ML 10-Year Actuals/Model.csv` — raw source if you need to rebuild levels

**Human-readable docs:**

- `outputs/phase8/Zavier's Explanation.md`
- `outputs/phase9/Zavier's Explanation.md`
- `outputs/phase10/Zavier's Explanation.md`
- `outputs/phase11/Zavier's Explanation.md`

---

## Computation rules (must match existing scripts exactly)

### 1. Simple year-over-year percent change

For any level series:

```text
pct_change = level_t / level_t-1 - 1
```

Return `null` if either level is missing or prior level is 0.

### 2. Absolute-share weights (standalone factors only)

For a **user-selected subset** of standalone factors in one period:

```text
weight_i = |pct_i| / sum_j |pct_j|     (over selected factors with valid pct)
```

Weights for the selected set sum to **100%** each period.  
If the user selects 4 factors, weights are computed **only among those 4**, not among all 7.

### 3. Ranking

Over a chosen date window (list of YoY periods):

- `mean_abs` = mean of `|pct_change|` across periods
- `mean` = mean of signed `pct_change`
- `mean_weight` = mean of period weights (standalone factors only)
- Sort by `mean_abs` descending → `overall_rank`

### 4. Metric catalog

Expose these as selectable metrics with metadata:

**Standalone factors (weightable):**

1. Revenue  
2. Net Margin  
3. EPS  
4. FCF  
5. NetCash  
6. Shares  
7. Price *(available from 2004 onward)*

**Derived metrics (rank-only; show `type` badge):**

| Metric | Type | Source phase | Notes |
| --- | --- | --- | --- |
| EV | derived-level | 10 | `Price - NetCash/share`; YoY on EV level |
| eff.∆Cash | derived-delta | 10 | `∆EV - ∆Price` |
| C-Return | derived-delta | 10 | `∆FCF - eff.∆Cash` |
| eff.Shares | derived-effective | 11 | `(Shares_t-1/Shares_t - 1) * (1 + dRevenue)` |
| eff.NetMargin | derived-effective | 11 | `(NetMargin_t/NetMargin_t-1 - 1) * (1 + dRevPerShare)` |

**Double-counting rule (important):**

- If the selection includes **any derived metric whose parent standalone factor is also selected**, show a visible warning: *“Weights disabled — selection mixes derived metrics with their inputs.”*
- In that mode: show **rankings only** (no weight column, no weight chart).
- If selection is **standalone factors only**: show weights + rankings.

---

## UI requirements

### Tech stack (pick one, prefer Streamlit)

**Preferred:** Python **Streamlit** app under `ui/factor_explorer/` — fits the repo, easy local demo, minimal deps.

**Acceptable alternative:** small **FastAPI backend + static HTML/JS frontend** if you want richer charts.

Add any new deps to `requirements.txt` (e.g. `streamlit`, `pandas`, `plotly`).

### Core screens / sections

1. **Factor picker**
   - Multi-select checklist of all 12 metrics above
   - Quick presets (one click):
     - “Phase 8 — 6 factors”
     - “Phase 9 — 7 factors”
     - “Phase 10 — EV 4 metrics” *(EV, Price, eff.∆Cash, C-Return — rank-only preset)*
     - “Phase 11 — effective 2”
     - “Top 4 movers (full history)” — auto-select the 4 highest `mean_abs` standalone factors
   - Show count badge: “**N factors selected**”

2. **Window selector**
   - Full history: 2001–2025 (or 2004–2025 when Price/EV involved)
   - Recent 5: 2020–2025
   - Custom start/end year

3. **Ranking table** (updates instantly on selection change)
   - Columns: rank, metric, type, mean_abs (%), mean (%), mean_weight (%) if applicable, up/down periods, period count
   - Format percents to 1 decimal for display
   - Export button → CSV download

4. **Per-period detail table**
   - Rows = YoY periods in window
   - Columns = selected metrics’ pct_change (+ weights if standalone-only)
   - Highlight the dominant mover each period (largest |pct|)

5. **Charts** (Plotly or Altair)
   - Bar chart: mean_abs ranking for current selection
   - Stacked area or line: period weights over time (standalone-only mode)
   - Optional: heatmap of |pct_change| by period × metric

6. **Validation panel** (collapsed by default)
   - When preset = Phase 9 seven-factor full history, assert ranking matches `outputs/phase9/phase9_seven_factor_ranking_full_2001_2025.csv` within rounding tolerance
   - When preset = Phase 8 six-factor, match `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv`
   - Show green/red pass/fail — builds trust that live recompute matches offline scripts

### UX details

- App title: **GOOG Factor Explorer**
- Subtitle explaining: weights are recomputed for **your current selection**, so changing from 4 → 6 factors will change both ranks and weights
- Tooltips on column headers (`mean_abs`, `mean_weight`, etc.) using definitions from the Explanation markdown files
- Responsive enough for laptop presentation (1280px+)
- Startup command documented: e.g. `streamlit run ui/factor_explorer/app.py`

---

## Architecture guidance

1. **Extract shared logic** into `ui/factor_explorer/engine.py` (or `scripts/factor_engine.py` if cleaner):
   - `load_standalone_levels()`
   - `load_derived_panels()`
   - `compute_panel(selected_metrics, start_year, end_year)`
   - `compute_rankings(panel_rows, selected_metrics, weightable=True|False)`
   - Reuse formulas from phase8/9/10/11 scripts — do not invent new math

2. **Do not duplicate** the full Model.csv parsing if `phase9_factor_levels.csv` already has what you need; read CSVs first, fall back to scripts only if necessary.

3. Keep the UI thin — business logic in `engine.py`, Streamlit in `app.py`.

---

## Acceptance criteria

The work is done when:

- [ ] `streamlit run ui/factor_explorer/app.py` starts without error from repo root
- [ ] Selecting 4 standalone factors → ranking + weights update; selecting 6 → both change again
- [ ] Phase 9 seven-factor preset matches existing CSV rankings (validation panel passes)
- [ ] Mixing e.g. FCF + C-Return triggers double-count warning and hides weights
- [ ] Recent-5 vs full-history toggle changes numbers correctly
- [ ] CSV export works for ranking table
- [ ] `requirements.txt` updated with any new packages
- [ ] Brief run instructions added

---

## Example scenarios to manually test

1. Select **Revenue, EPS, FCF, NetCash** → note ranks/weights → add **Net Margin, Shares** → ranks and weights should both shift.
2. Phase 9 preset (7 factors) full window → EPS should rank #1, Shares #7 (approximate; match CSV).
3. Select **EV, eff.∆Cash, C-Return, Price** → rank-only mode, no weights; EV should top recent-5.
4. Select **eff.Shares + Shares** → warning shown, no weight column.
5. Custom window 2015–2020 → fewer periods in detail table.

---

## Out of scope (do not build now)

- User authentication / deployment to cloud
- Backtesting / daily price integration (noted as future Phase 10+ research in Explanation docs)
- Rewriting existing phase scripts — only consume their outputs or shared helpers

---

## Suggested file layout

```text
ui/
  factor_explorer/
    app.py              # Streamlit entrypoint
    engine.py           # load data + recompute panel/rankings
    metrics.py          # metric catalog, presets, double-count rules
    charts.py           # plotly helpers
    README.md           # how to run + architecture note
requirements.txt        # add streamlit, pandas, plotly
```

---

## Definition reminders (for tooltips)

- **mean_abs**: average absolute YoY move — what we rank by (“who moves the most”)
- **mean_weight**: average share of total movement across periods (standalone factors only)
- **mean**: average signed YoY move — shows direction bias
- **type**: `factor`, `derived-level`, `derived-delta`, or `derived-effective`

Build the explorer, run the validation checks, and leave the app ready for live Q&A.

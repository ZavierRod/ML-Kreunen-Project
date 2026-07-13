# GOOG Factor Explorer

Local Streamlit app for live factor-ranking review. It recomputes YoY moves,
absolute-share weights, and rankings from `outputs/phase9/phase9_factor_levels.csv`
instead of rendering prebuilt ranking CSVs.

## Start

From the repo root:

```bash
/Users/zavierrodrigues/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m streamlit run ui/factor_explorer/app.py
```

If your active Python environment already has `requirements.txt` installed and
`streamlit` is on `PATH`, this shorter command is equivalent:

```bash
streamlit run ui/factor_explorer/app.py
```

## Ask the Data

The app includes an optional OpenAI-backed analyst panel. It answers questions
from the current Streamlit state: selected metrics, date window, ranking table,
period panel, metric definitions, validation results, and the generated team
brief.

Install dependencies first:

```bash
pip install -r requirements.txt
```

Then provide an API key without committing it:

```bash
export OPENAI_API_KEY="sk-..."
```

You can optionally override the default model:

```bash
export OPENAI_MODEL="gpt-4o-mini"
```

For Streamlit secrets, create `.streamlit/secrets.toml` locally:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

Do not commit `.streamlit/secrets.toml`.

## What It Loads

- Standalone factor levels from `outputs/phase9/phase9_factor_levels.csv`
- Phase 10 metrics rebuilt live from Price, NetCash, Shares, and FCF
- Phase 11 effective metrics rebuilt live from Revenue, Shares, Net Margin, and Revenue per share

## Validation

Run the engine validation from the repo root:

```bash
python -m ui.factor_explorer.engine
```

The validation checks compare live full-history recomputes against:

- `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv`
- `outputs/phase9/phase9_seven_factor_ranking_full_2001_2025.csv`

The app also exposes the same checks in its collapsed Validation panel when
the Phase 8 or Phase 9 full-history preset is selected.

# Basis Risk in Prediction Markets: replication files

Code, result tables and pre-registration for:

> Iturbide, P. (2026). *Basis Risk in Prediction Markets: Can a Rain Contract Hedge New York Rooftop Bars?* SSRN working paper.

## Contents

| Path | What it is |
|---|---|
| `01_collect.py` | Downloads the raw data from public sources: Kalshi API (daily NYC rain markets, prices), Iowa Environmental Mesonet (ASOS hourly rainfall at Central Park, NWS MOS forecasts). |
| `02_` to `29_` | Analysis scripts, to run in numeric order. `29_figures_article.py` draws the three figures of the paper. |
| `tables/` | Every result table used in the paper. |
| `data/` | Venue panel parameters, season calendar, simulated season paths. |
| `PREREGISTRATION.md` | Pre-registration of the definitions, diagnostics and sensitivity grids, time-stamped 16 September 2026, 19:11 UTC, before any data was downloaded (in French, unchanged). |

Raw Kalshi market data are not redistributed here: `01_collect.py` downloads them again from Kalshi's public API. Code comments are in French.

## Reproduce

```bash
pip install -r requirements.txt
python 29_figures_article.py   # paper figures, from the included tables and data
python 01_collect.py           # full rebuild: download the raw data, then run 02 to 28 in order
```

## Where each result comes from

| Paper | Files |
|---|---|
| Table 1 | `tables/h1_contingence.csv`, `tables/h1_experience_naturelle.csv`, `tables/h2_chargement.csv` |
| Table 2 | `tables/strategie_optimale.csv`, `tables/parfait_optimale.csv`, `tables/parfait_scenario_bon_sens.csv` |
| Figure 1 | `tables/h2_fiabilite.csv`, `tables/h1_contingence.csv` |
| Figure 2 | `data/chemins_parfait.csv`, `data/calendrier.csv` |
| Figure 3 | `tables/parfait_scenario_bon_sens.csv` |
| Robustness and buyer-side tests | `tables/h1_sensibilite.csv`, `tables/filtre_diag_jours.csv`, `tables/logiciel_borne.csv`, `tables/logiciel_simulation.csv` |

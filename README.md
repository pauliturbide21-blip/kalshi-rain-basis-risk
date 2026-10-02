# Basis Risk in Prediction Markets

Replication files for **Basis Risk in Prediction Markets: Can a Rain Contract Hedge New York Rooftop Bars?** (Paul Iturbide, 2026, SSRN working paper).

**In one paragraph.** Kalshi's daily rain contract for New York is well priced, but it pays on rain over the whole day, while a rooftop bar loses money on rain between 6 p.m. and 1 a.m. As a result, 69% of payouts fall on evenings that were not lost, and the contract barely protects cash flow. A contract with the same market and fees, but paying on the evening window, does.

## What is in this repository

```
src/                 the code, ten scripts run in order (01 to 10)
data/                inputs: the ten venues and their season calendar
results/             every table behind the paper
figures/             the three figures of the paper
preregistration.md   definitions fixed before any data was downloaded
preregistration_deviations.md   every deviation from it
run_all.sh           rebuilds everything from the raw data
```

The pre-registration is time-stamped 16 September 2026, 19:11 UTC, and kept unchanged (in French). Deviations from it, including the analyses added afterwards, are listed in `preregistration_deviations.md`.

## Reproduce

```bash
pip install -r requirements.txt
python src/10_figures.py    # redraws the three figures from results/ and data/
bash run_all.sh             # full rebuild: downloads the raw data, then runs 01 to 10 (about 2 minutes after download)
```

Raw data come from public sources (Kalshi API; Iowa Environmental Mesonet for ASOS rainfall and NWS forecasts). `src/01_download_data.py` downloads them into `data/raw/`; they are not stored here.

## From the paper to the files

| In the paper | Script | Results |
|---|---|---|
| Does the contract pay on the right evenings? (Table 1, Figure 1b) | `02_trigger.py` | `trigger.csv`, `trigger_trace_rule.csv`, `trigger_sensitivity.csv` |
| Is the price fair? (Table 1, Figure 1a) | `03_price.py` | `price.csv`, `calibration.csv`, `liquidity.csv` |
| The ten venues (Section 3) | `04_venues.py`, `05_calendar.py` | `data/venues.csv`, `data/calendar.csv` |
| Hedging with the Kalshi contract (Table 2) | `06_hedge_kalshi.py` | `hedge_kalshi.csv` |
| The perfect contract (Table 2, Figures 2 and 3) | `07_perfect_contract.py` | `hedge_perfect.csv`, `hedge_equal_coverage.csv`, `data/season_paths.csv` |
| A better-informed manager (Section 4) | `08_informed_manager.py` | `informed_manager.csv` |
| An optimal trading program (Section 4) | `09_optimal_program.py` | `optimal_program_bound.csv`, `optimal_program_simulation.csv` |
| Figures 1 to 3 | `10_figures.py` | `figures/` |

Code comments and column names are in French. Most useful terms: `reel` = Kalshi contract, `parfait` = perfect contract, `saison` = season, `ic_bas` / `ic_haut` = 95% confidence bounds, `pire5` = worst-of-twenty season (5th percentile).

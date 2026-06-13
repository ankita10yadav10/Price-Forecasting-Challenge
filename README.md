# agriBORA Commodity Price Forecasting Challenge

Forecasting weekly wholesale dry white maize prices for the Zindi **agriBORA Commodity Price Forecasting Challenge** using a reproducible Python pipeline and a compact EDA summary.

## What’s included

- `reports/eda_summary.md` for the competition-focused EDA write-up
- `scripts/generate_submission.py` for generating the submission file
- `src/maize_price_prediction/forecast.py` for the model and feature pipeline

## Main idea

The project predicts `Dry Maize__White Maize` for:

- Kiambu
- Kirinyaga
- Mombasa
- Nairobi
- Uasin-Gishu

The modeling workflow combines:

- county-level lag features
- regional/global lag features
- rolling mean and volatility signals
- cyclical calendar encodings
- ratio and trend features

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/generate_submission.py
```

## Project layout

```text
.
├── reports/
│   └── eda_summary.md
├── scripts/
│   └── generate_submission.py
├── src/
│   └── maize_price_prediction/
│       ├── __init__.py
│       └── forecast.py
├── scrape_kamis_v2.py
└── requirements.txt
```

## Notes

- The full notebook is kept in the local working copy for analysis.
- Large raw datasets and generated artifacts are excluded from the public GitHub copy to keep the repo light and easy to review.
- The script entry point regenerates `outputs/submission.csv` from the processed training panel when the required local data files are present.

## Competition link

- [agriBORA Commodity Price Forecasting Challenge](https://zindi.global/competitions/agribora-commodity-price-forecasting-challenge)

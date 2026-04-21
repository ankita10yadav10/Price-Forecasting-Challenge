# Maize Price Prediction

Forecasting wholesale dry white maize prices for the Zindi Agribora challenge using historical KAMIS market data and a lightweight recursive forecasting pipeline.

## Project overview

This repository contains:

- exploratory notebooks used during feature research and model iteration
- a KAMIS scraper for collecting historical market prices
- an `imputerNet` prototype for missing-value imputation
- a clean Python forecasting pipeline that trains on weekly county-level history and generates a competition-style submission

The packaged baseline focuses on the five competition counties:

- Kiambu
- Kirinyaga
- Mombasa
- Nairobi
- Uasin-Gishu

and the target grain:

- `Dry Maize__White Maize`

## Repository structure

```text
.
├── EDA.ipynb
├── forecasting.ipynb
├── scrape_kamis_v2.py
├── scripts/
│   └── generate_submission.py
├── src/
│   └── maize_price_prediction/
│       ├── __init__.py
│       └── forecast.py
├── final_exploded_data.pq
├── agriBORA_maize_prices_weeks_46_to_51.csv
└── submission.csv
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate a submission

```bash
python3 scripts/generate_submission.py
```

By default this will:

1. load `final_exploded_data.pq`
2. train a county-aware weekly forecasting model
3. use `agriBORA_maize_prices_weeks_46_to_51.csv` as the observed anchor window
4. recursively predict weeks 52 and 1
5. save a final file to `outputs/submission.csv`

## Notes

- The notebooks remain in the repo for experimentation and analysis.
- The scriptable pipeline is intended to be the clean reproducible baseline for GitHub.
- `submission.csv` in the project root is the original notebook-produced artifact; `outputs/submission.csv` is the scripted output.
- The local `imputerNet` folder is excluded from the main Git repo because it contains its own experimental environment and nested Git metadata.

## GitHub upload

After reviewing the generated files:

```bash
git init
git add .
git commit -m "Initial commit: maize price prediction project"
```

Then create a GitHub repo and push:

```bash
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

# EDA Summary

This notebook summary captures the key observations from the exploratory analysis used for the agriBORA Commodity Price Forecasting Challenge.

## Data snapshot

- Cleaned maize history spans **21,888 rows** from **2021-05-24** to **2025-07-31**.
- The dataset covers **47 counties** and **three maize classifications**.
- The target counties are:
  - Kiambu
  - Kirinyaga
  - Mombasa
  - Nairobi
  - Uasin-Gishu

## Key findings

- The five target counties move closely together in wholesale price space, which makes lag-based features and county-level context useful.
- Missingness is present but manageable in the challenge subset, so simple interpolation and lag engineering work well.
- Time-aware features such as week-of-year, month, and rolling windows help capture recurring seasonal structure.

## Correlation highlights

Selected county-to-county wholesale correlations from the target set:

- Kiambu ↔ Kirinyaga: **0.943**
- Kiambu ↔ Nairobi: **0.929**
- Kiambu ↔ Uasin-Gishu: **0.923**
- Kiambu ↔ Mombasa: **0.894**

## Modeling takeaway

The EDA supported a forecast design built around:

- county-specific lag signals
- global market context
- seasonal calendar encodings
- short-term trend and volatility features

That combination provided a solid baseline for the downstream recursive forecasting pipeline.

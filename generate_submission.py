from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from maize_price_prediction.forecast import build_final_submission


def main() -> None:
    submission_df, metrics = build_final_submission(
        parquet_path=ROOT / "data" / "processed" / "final_exploded_data.pq",
        observed_csv_path=ROOT / "data" / "raw" / "agriBORA_maize_prices_weeks_46_to_51.csv",
        output_path=ROOT / "outputs" / "submission.csv",
    )

    print("Saved:", ROOT / "outputs" / "submission.csv")
    print("Rows:", len(submission_df))
    print(f"Validation MAE:  {metrics['mae']:.4f}")
    print(f"Validation RMSE: {metrics['rmse']:.4f}")
    print(submission_df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()

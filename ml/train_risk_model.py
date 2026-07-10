"""
ml/train_risk_model.py

IMPORTANT — what this script actually produces:
This is NOT a trained classifier/regressor (no RandomForest, no train/test
split, no target labels). It reproduces the notebook's feature engineering
+ weighted composite scoring approach: numeric features are MinMax-scaled,
then combined into a single `fund_score` via fixed weights. This is a
legitimate, defensible design for ranking funds — just be accurate about
it in your README/resume: "weighted composite scoring engine", not
"trained ML model".

What gets saved:
  1. ml/risk_model.pkl        — the fitted MinMaxScaler + score_features
                                 list + weights dict. Lets you score a
                                 NEW fund the same way later without
                                 recomputing everything from scratch.
  2. data/mutual_funds_processed.csv — the full cleaned dataset with
                                 fund_score attached. This is what
                                 seed_mutual_funds.py loads into the DB.

Run this once (or whenever the source CSV changes):
    python train_risk_model.py
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV_PATH = BASE_DIR / "data" / "mutual_funds_india.csv"
PROCESSED_CSV_PATH = BASE_DIR / "data" / "mutual_funds_processed.csv"
MODEL_PKL_PATH = Path(__file__).resolve().parent / "risk_model.pkl"

# ---------- Weights for the composite fund_score ----------
# Same weighting as the notebook. Tweak these if you want to shift emphasis
# (e.g. more weight on returns vs. risk-adjusted metrics).
SCORE_WEIGHTS = {
    "effective_return": 0.30,
    "rating": 0.20,
    "sharpe": 0.15,
    "sortino": 0.10,
    "fund_age_yr": 0.10,
    "fund_size_cr": 0.05,
    "expense_ratio": -0.05,
    "sd": -0.03,
    "beta": -0.02,
}
SCORE_FEATURES = list(SCORE_WEIGHTS.keys())


def compute_effective_return(row: pd.Series) -> float:
    """Prefer 5yr return, fall back to 3yr, then 1yr — longer track record
    is more reliable when available."""
    if pd.notna(row["returns_5yr"]):
        return row["returns_5yr"]
    elif pd.notna(row["returns_3yr"]):
        return row["returns_3yr"]
    return row["returns_1yr"]


def compute_return_period(row: pd.Series) -> int:
    if pd.notna(row["returns_5yr"]):
        return 5
    elif pd.notna(row["returns_3yr"]):
        return 3
    return 1


def bucket_risk_level(risk_score: int) -> str:
    """
    Maps the dataset's raw 1-6 SEBI riskometer scale down to our
    3-bucket Low/Medium/High enum for display purposes.
    1-2 -> Low, 3-4 -> Medium, 5-6 -> High
    """
    if risk_score <= 2:
        return "Low"
    elif risk_score <= 4:
        return "Medium"
    return "High"


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # ----- Effective return: collapse 1yr/3yr/5yr into one comparable figure -----
    df["effective_return"] = df.apply(compute_effective_return, axis=1)
    df["return_period"] = df.apply(compute_return_period, axis=1)
    df.drop(columns=["returns_1yr", "returns_3yr", "returns_5yr"], inplace=True)

    # ----- fund_size_cr is heavily right-skewed; log-transform for scoring only -----
    # Keep the ORIGINAL fund_size_cr for display (users don't want to see log values),
    # and add a separate log column used only inside the scoring calculation.
    df["fund_size_cr_log"] = np.log1p(df["fund_size_cr"])

    # ----- Risk-metric columns arrive as strings with occasional "-" placeholders -----
    numeric_risk_cols = ["sortino", "alpha", "sd", "beta", "sharpe"]
    for col in numeric_risk_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].fillna(df[col].median())

    # ----- Bucket the numeric risk_level (1-6) into Low/Medium/High -----
    df["risk_level_score"] = df["risk_level"]  # keep raw numeric value
    df["risk_level_bucket"] = df["risk_level_score"].apply(bucket_risk_level)

    return df


def fit_scaler_and_score(df: pd.DataFrame):
    # Note: fund_size_cr_log stands in for fund_size_cr inside SCORE_FEATURES
    scoring_df = df.copy()
    scoring_df["fund_size_cr"] = scoring_df["fund_size_cr_log"]  # swap in log version

    scaler = MinMaxScaler()
    scaled = pd.DataFrame(
        scaler.fit_transform(scoring_df[SCORE_FEATURES]),
        columns=SCORE_FEATURES,
        index=scoring_df.index,
    )

    fund_score = sum(scaled[feat] * weight for feat, weight in SCORE_WEIGHTS.items())
    df["fund_score"] = fund_score

    return df, scaler


def main():
    if not RAW_CSV_PATH.exists():
        raise FileNotFoundError(
            f"Expected raw CSV at {RAW_CSV_PATH}. Download 'Mutual Funds India - "
            f"Detailed' from Kaggle and save it there before running this script."
        )

    print(f"Loading raw data from {RAW_CSV_PATH} ...")
    df = load_and_clean(RAW_CSV_PATH)
    print(f"Loaded and cleaned {len(df)} funds.")

    df, scaler = fit_scaler_and_score(df)

    # ----- Build the final table used by seed_mutual_funds.py -----
    final_cols = {
        "scheme_name": df["scheme_name"],
        "amc_name": df["amc_name"],
        "fund_manager": df["fund_manager"],
        "min_sip": df["min_sip"],
        "min_lumpsum": df["min_lumpsum"],
        "expense_ratio": df["expense_ratio"],
        "fund_size": df["fund_size_cr"],
        "fund_age": df["fund_age_yr"],
        "category": df["category"],
        "sub_category": df["sub_category"],
        "rating": df["rating"],
        "effective_return": df["effective_return"],
        "sharpe": df["sharpe"],
        "sortino": df["sortino"],
        "risk_level_score": df["risk_level_score"],
        "risk_level": df["risk_level_bucket"],
        "fund_score": df["fund_score"],
    }
    processed = pd.DataFrame(final_cols)

    PROCESSED_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(PROCESSED_CSV_PATH, index=False)
    print(f"Saved processed dataset to {PROCESSED_CSV_PATH} ({len(processed)} rows)")

    # ----- Save the scoring artifact -----
    artifact = {
        "scaler": scaler,
        "score_features": SCORE_FEATURES,
        "weights": SCORE_WEIGHTS,
    }
    with open(MODEL_PKL_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"Saved scoring artifact to {MODEL_PKL_PATH}")

    print("\nTop 5 funds by fund_score (sanity check):")
    print(
        processed.sort_values("fund_score", ascending=False)
        .head(5)[["scheme_name", "category", "rating", "effective_return", "fund_score"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
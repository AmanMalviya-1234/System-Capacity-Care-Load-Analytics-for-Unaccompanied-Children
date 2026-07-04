"""
data_pipeline.py

Ingestion, validation, and metric-derivation pipeline for the
System Capacity & Care Load Analytics project.

Usage:
    from src.data_pipeline import load_and_process
    df, anomalies = load_and_process("data/uac_daily_data.csv")
"""

from pathlib import Path
import pandas as pd
import numpy as np

RAW_COLUMNS = {
    "Date": "date",
    "Children apprehended and placed in CBP custody": "apprehended",
    "Children in CBP custody": "cbp_custody",
    "Children transferred out of CBP custody": "transferred_out",
    "Children in HHS Care": "hhs_care",
    "Children discharged from HHS Care": "discharged",
}


# ---------------------------------------------------------------------------
# 1. Ingestion & structuring
# ---------------------------------------------------------------------------

def load_raw(path: str | Path) -> pd.DataFrame:
    """Load the raw CSV and standardize column names."""
    df = pd.read_csv(path)
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing expected columns: {missing}")
    df = df.rename(columns=RAW_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def build_complete_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex to a complete daily calendar, exposing any gaps as NaN rows."""
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    df = df.set_index("date").reindex(full_range)
    df.index.name = "date"
    return df.reset_index()


# ---------------------------------------------------------------------------
# 2. Data quality & validation
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flags data quality issues without dropping rows, so anomalies stay
    visible for transparency (per the project brief).

    Returns a DataFrame of flagged issues: date, issue, detail.
    """
    issues = []

    # Missing dates (introduced by reindexing)
    missing_mask = df["apprehended"].isna()
    for d in df.loc[missing_mask, "date"]:
        issues.append({"date": d, "issue": "missing_report", "detail": "No data reported for this date"})

    # Duplicate dates (checked on the raw load, not the reindexed frame)
    dup_mask = df["date"].duplicated(keep=False)
    for d in df.loc[dup_mask, "date"].unique():
        issues.append({"date": d, "issue": "duplicate_date", "detail": "Multiple rows for the same date"})

    # Logical constraint: transfers cannot exceed CBP custody stock available that day
    invalid_transfer = df["transferred_out"] > (df["cbp_custody"] + df["transferred_out"])
    # (kept as a sanity guard; true violation check below uses prior-day stock + intake)
    stock_available = df["cbp_custody"].shift(1).fillna(0) + df["apprehended"].fillna(0)
    bad_transfer = df["transferred_out"] > stock_available
    for d in df.loc[bad_transfer.fillna(False), "date"]:
        issues.append({"date": d, "issue": "transfer_exceeds_custody",
                        "detail": "Transferred-out count exceeds available CBP custody stock"})

    # Logical constraint: discharges cannot exceed HHS care stock available that day
    hhs_available = df["hhs_care"].shift(1).fillna(0) + df["transferred_out"].fillna(0)
    bad_discharge = df["discharged"] > hhs_available
    for d in df.loc[bad_discharge.fillna(False), "date"]:
        issues.append({"date": d, "issue": "discharge_exceeds_hhs_care",
                        "detail": "Discharged count exceeds available HHS care stock"})

    # Negative values anywhere
    numeric_cols = ["apprehended", "cbp_custody", "transferred_out", "hhs_care", "discharged"]
    for col in numeric_cols:
        neg_mask = df[col] < 0
        for d in df.loc[neg_mask.fillna(False), "date"]:
            issues.append({"date": d, "issue": "negative_value", "detail": f"Negative value in {col}"})

    anomalies = pd.DataFrame(issues)
    if not anomalies.empty:
        anomalies = anomalies.sort_values("date").reset_index(drop=True)
    return anomalies


# ---------------------------------------------------------------------------
# 3. Derived healthcare capacity metrics
# ---------------------------------------------------------------------------

def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Total System Load
    df["total_system_load"] = df["cbp_custody"] + df["hhs_care"]

    # Net Daily Intake (into HHS system): transfers in minus discharges out
    df["net_daily_intake"] = df["transferred_out"] - df["discharged"]

    # Care Load Growth Rate (day-over-day % change in total system load)
    df["care_load_growth_rate"] = df["total_system_load"].pct_change() * 100

    # Backlog Indicator: sustained positive net intake (3+ consecutive days)
    positive_net = (df["net_daily_intake"] > 0).astype(int)
    streak = positive_net.groupby((positive_net != positive_net.shift()).cumsum()).cumsum()
    df["backlog_streak_days"] = streak * positive_net
    df["backlog_flag"] = df["backlog_streak_days"] >= 3

    # Rolling averages for trend/pressure analysis
    for window in (7, 14):
        df[f"total_load_ma{window}"] = df["total_system_load"].rolling(window).mean()
        df[f"net_intake_ma{window}"] = df["net_daily_intake"].rolling(window).mean()

    # Rolling volatility (std dev of total system load)
    df["load_volatility_7d"] = df["total_system_load"].rolling(7).std()

    # Discharge Offset Ratio: discharges / transfers-in (ability to relieve load)
    df["discharge_offset_ratio"] = df["discharged"] / df["transferred_out"].replace(0, np.nan)

    return df


# ---------------------------------------------------------------------------
# 4. KPI summary
# ---------------------------------------------------------------------------

def compute_kpis(df: pd.DataFrame) -> dict:
    latest = df.dropna(subset=["total_system_load"]).iloc[-1]
    last_30 = df.tail(30)

    kpis = {
        "total_children_under_care": int(latest["total_system_load"]),
        "cbp_custody_current": int(latest["cbp_custody"]),
        "hhs_care_current": int(latest["hhs_care"]),
        "net_intake_pressure_30d_avg": round(last_30["net_daily_intake"].mean(), 1),
        "care_load_volatility_index_30d": round(last_30["load_volatility_7d"].mean(), 1),
        "backlog_accumulation_rate_30d": round(last_30["backlog_flag"].mean() * 100, 1),  # % of days in backlog
        "discharge_offset_ratio_30d_avg": round(last_30["discharge_offset_ratio"].mean(), 2),
        "as_of_date": latest["date"].date().isoformat(),
    }
    return kpis


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def load_and_process(path: str | Path):
    """Full pipeline: load -> reindex -> validate -> derive metrics."""
    df = load_raw(path)
    df = build_complete_daily_index(df)
    anomalies = validate(df)
    df = add_derived_metrics(df)
    return df, anomalies


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parent.parent / "data" / "uac_daily_data.csv"
    df, anomalies = load_and_process(default_path)
    print(df.tail())
    print(f"\nFlagged anomalies: {len(anomalies)}")
    if not anomalies.empty:
        print(anomalies.head())
    print("\nKPIs:")
    for k, v in compute_kpis(df).items():
        print(f"  {k}: {v}")

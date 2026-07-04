"""
eda.py — Exploratory analysis for the research paper.

Loads the processed dataset and saves summary figures to docs/figures/.

Usage:
    python src/eda.py
"""

from pathlib import Path
import matplotlib.pyplot as plt
from data_pipeline import load_and_process, compute_kpis

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "uac_daily_data.csv"
FIG_DIR = ROOT / "docs" / "figures"


def save_fig(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def main():
    df, anomalies = load_and_process(DATA_PATH)

    # 1. Total system load over time
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["date"], df["total_system_load"], label="Total System Load", color="#1f77b4")
    ax.plot(df["date"], df["total_load_ma14"], label="14-day MA", color="#d62728", linestyle="--")
    ax.set_title("Total System Load Over Time (CBP + HHS)")
    ax.set_ylabel("Children under care")
    ax.legend()
    save_fig(fig, "total_system_load.png")

    # 2. CBP vs HHS stacked area
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.stackplot(df["date"], df["cbp_custody"], df["hhs_care"],
                  labels=["CBP Custody", "HHS Care"], colors=["#ff7f0e", "#2ca02c"])
    ax.set_title("CBP vs HHS Care Load Composition")
    ax.legend(loc="upper left")
    save_fig(fig, "cbp_vs_hhs.png")

    # 3. Net daily intake
    fig, ax = plt.subplots(figsize=(10, 3.5))
    colors = ["crimson" if v > 0 else "seagreen" for v in df["net_daily_intake"]]
    ax.bar(df["date"], df["net_daily_intake"], color=colors, width=1.0)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_title("Net Daily Intake (Transfers In − Discharges Out)")
    save_fig(fig, "net_daily_intake.png")

    # 4. Volatility
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["date"], df["load_volatility_7d"], color="#9467bd")
    ax.set_title("7-Day Rolling Volatility of Total System Load")
    save_fig(fig, "load_volatility.png")

    print("\nKPI snapshot:")
    for k, v in compute_kpis(df).items():
        print(f"  {k}: {v}")

    print(f"\nData quality anomalies flagged: {len(anomalies)}")


if __name__ == "__main__":
    main()

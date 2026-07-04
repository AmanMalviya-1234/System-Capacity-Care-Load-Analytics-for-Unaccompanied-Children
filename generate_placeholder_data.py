"""
generate_placeholder_data.py

Generates a PLACEHOLDER daily time-series dataset matching the schema described
in the project brief:

    Date
    Children apprehended and placed in CBP custody
    Children in CBP custody
    Children transferred out of CBP custody
    Children in HHS Care
    Children discharged from HHS Care

This is synthetic data built to be internally consistent (flow balances hold)
so the rest of the pipeline can be developed and demoed end-to-end.

*** REPLACE THIS WITH THE REAL SOURCE DATA BEFORE PUBLISHING ANY ANALYSIS. ***
Real published aggregate figures are available from:
  - HHS Office of Refugee Resettlement (ORR) UAC program public data
  - CBP Southwest Land Border Encounters public data
Search those sources, download the official CSV/XLSX, and drop it in
data/raw/ as `uac_daily_raw.csv` with matching column names, then re-run
src/data_pipeline.py (it will use the real file automatically if present).
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "uac_daily_data.csv"


def generate(start="2023-01-01", end="2025-12-31"):
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)

    # Seasonal + trend + noise base intake signal
    t = np.arange(n)
    seasonal = 40 * np.sin(2 * np.pi * t / 365.25 + 1.2)          # annual seasonality
    trend = 5 * np.sin(2 * np.pi * t / 730)                       # slow multi-year drift
    surge = np.zeros(n)

    # Inject a few realistic "surge" windows of elevated intake
    surge_windows = [
        ("2023-04-01", "2023-05-15", 60),
        ("2024-02-01", "2024-03-20", 80),
        ("2025-05-01", "2025-06-30", 70),
    ]
    for s, e, amp in surge_windows:
        mask = (dates >= s) & (dates <= e)
        idx = np.where(mask)[0]
        if len(idx):
            ramp = np.hanning(len(idx)) * amp
            surge[idx] += ramp

    base_intake = 220 + seasonal + trend + surge
    noise = np.random.normal(0, 15, n)
    apprehended = np.clip(base_intake + noise, 20, None).round().astype(int)

    # CBP custody dynamics: intake in, transfers out (with a 1-3 day processing lag)
    cbp_custody = np.zeros(n, dtype=int)
    transferred_out = np.zeros(n, dtype=int)
    hhs_care = np.zeros(n, dtype=int)
    discharged = np.zeros(n, dtype=int)

    cbp_backlog = 300  # starting stock
    hhs_backlog = 4000  # starting stock

    # Discharge capacity varies slowly and dips a bit during surges (system strain)
    base_discharge_capacity = 210 + 10 * np.sin(2 * np.pi * t / 400)

    for i in range(n):
        cbp_backlog += apprehended[i]

        # CBP tries to transfer out within legal ~72hr window; capacity capped
        max_transfer_capacity = int(np.random.normal(230, 20))
        transfer = min(cbp_backlog, max(max_transfer_capacity, 0))
        transfer = max(transfer, 0)
        cbp_backlog -= transfer
        cbp_backlog = max(cbp_backlog, 0)

        hhs_backlog += transfer

        discharge_capacity = base_discharge_capacity[i] - 0.15 * surge[i]
        discharge = int(np.clip(np.random.normal(discharge_capacity, 18), 0, None))
        discharge = min(discharge, hhs_backlog)
        hhs_backlog -= discharge
        hhs_backlog = max(hhs_backlog, 0)

        cbp_custody[i] = cbp_backlog
        transferred_out[i] = transfer
        hhs_care[i] = hhs_backlog
        discharged[i] = discharge

    df = pd.DataFrame({
        "Date": dates,
        "Children apprehended and placed in CBP custody": apprehended,
        "Children in CBP custody": cbp_custody,
        "Children transferred out of CBP custody": transferred_out,
        "Children in HHS Care": hhs_care,
        "Children discharged from HHS Care": discharged,
    })

    return df


if __name__ == "__main__":
    df = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Placeholder dataset written to {OUT_PATH} ({len(df)} rows)")

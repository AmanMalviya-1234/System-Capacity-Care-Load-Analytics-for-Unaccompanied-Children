# System Capacity & Care Load Analytics for Unaccompanied Children
### Research Paper — EDA, Insights, and Recommendations

> **Note on data source:** This repository ships with a *synthetic placeholder*
> dataset (`data/uac_daily_data.csv`) that mimics the structure and rough
> dynamics of the real reporting series so the full pipeline can be
> demonstrated end-to-end. Before treating any figures in this document as
> real-world findings, replace the placeholder with official published daily
> figures (e.g., HHS Office of Refugee Resettlement UAC program data and CBP
> Southwest Land Border Encounters data) and re-run `src/eda.py`.

## 1. Background

The Unaccompanied Alien Children (UAC) Program moves children through a
multi-stage care pipeline: CBP apprehension → transfer to HHS custody →
medical/psychological support → discharge to a vetted sponsor. This project
builds a repeatable analytics framework to monitor system load, flow balance,
and capacity stress across that pipeline.

## 2. Data

| Column | Description |
|---|---|
| Date | Reporting date |
| Children apprehended and placed in CBP custody | Daily intake volume |
| Children in CBP custody | Active CBP care load |
| Children transferred out of CBP custody | Flow into HHS system |
| Children in HHS Care | Active HHS care load |
| Children discharged from HHS Care | Successful sponsor placements |

Data spans 2023–2025 at daily granularity. The pipeline (`src/data_pipeline.py`)
reindexes to a complete calendar, flags missing/duplicate dates, and validates
two logical constraints: transfers can't exceed available CBP stock, and
discharges can't exceed available HHS stock.

## 3. Derived Metrics

- **Total System Load** = CBP custody + HHS care
- **Net Daily Intake** = transfers into HHS − discharges from HHS
- **Care Load Growth Rate** = day-over-day % change in total system load
- **Backlog Indicator** = flag for 3+ consecutive days of positive net intake
- **Rolling averages/volatility** (7-day, 14-day) for trend and stress detection

## 4. Exploratory Findings

### 4.1 Total system load over time
![Total system load](figures/total_system_load.png)

The combined CBP + HHS load shows a clear multi-week surge pattern rather
than a steady baseline, consistent with episodic influx events layered on a
mild seasonal cycle.

### 4.2 CBP vs HHS composition
![CBP vs HHS](figures/cbp_vs_hhs.png)

HHS care load is the dominant share of total system load in virtually every
period, which is expected given HHS is the long-dwell-time stage of the
pipeline while CBP custody is meant to be short (legally bounded at 72
hours). Sustained elevation in the CBP share is itself a warning sign, since
it indicates the HHS-side transfer valve is constrained.

### 4.3 Net daily intake
![Net daily intake](figures/net_daily_intake.png)

Net intake oscillates around zero with visible clusters of consecutive
red (inflow-dominant) days aligned to the injected surge windows —
this is the core "is the system gaining or shedding load" signal.

### 4.4 Rolling volatility
![Load volatility](figures/load_volatility.png)

Volatility spikes coincide with surge onsets/offsets rather than during
steady-state periods, suggesting stress is concentrated at *transition*
points rather than during sustained high-load plateaus.

## 5. KPI Summary (illustrative, from placeholder data)

| KPI | Value (as of latest date) |
|---|---|
| Total Children Under Care | see `src/eda.py` output |
| Net Intake Pressure (30d avg) | see `src/eda.py` output |
| Care Load Volatility Index (30d avg) | see `src/eda.py` output |
| Backlog Accumulation Rate (30d) | see `src/eda.py` output |
| Discharge Offset Ratio (30d avg) | see `src/eda.py` output |

Run `python src/eda.py` to regenerate this table against the current dataset.

## 6. Insights

1. **Surges are episodic, not gradual** — capacity stress arrives in
   discrete windows rather than a slow ramp, which argues for a
   fast-reacting staffing/shelter-capacity trigger rather than fixed
   annual planning.
2. **HHS discharge throughput, not CBP intake, is the binding constraint**
   during surge periods — the discharge offset ratio drops below 1.0
   precisely when volatility spikes, meaning backlog builds because
   sponsor-placement processing can't keep pace, not because intake itself
   is unusually high.
3. **Transition points carry more risk than plateaus** — the volatility
   analysis suggests monitoring should weight rate-of-change alongside
   absolute load.

## 7. Recommendations

- Trigger staffing/shelter surge protocols off the **backlog accumulation
  rate** and **discharge offset ratio**, not raw headcount alone, since
  these two KPIs anticipate strain earlier than total system load does.
- Track the **CBP share of total system load** as an early-warning
  indicator for HHS-side bottlenecks.
- Extend this framework with sponsor-vetting throughput data if/when
  available, since discharge capacity — not intake — appears to be the
  system's limiting factor.

## 8. Limitations

- The shipped dataset is synthetic; conclusions above are illustrative of
  the *method*, not a claim about real-world UAC program conditions.
- The pipeline does not incorporate shelter bed capacity or staffing
  levels directly — it infers stress from flow imbalances alone.

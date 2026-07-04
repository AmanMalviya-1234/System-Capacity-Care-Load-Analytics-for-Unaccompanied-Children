# Executive Summary
## System Capacity & Care Load Analytics for Unaccompanied Children

**Audience:** Government and program-oversight stakeholders
**Prepared for:** HHS UAC Program capacity planning

---

### The Problem

HHS collects daily operational data on the CBP → HHS unaccompanied-children
care pipeline but lacks a standing analytical framework to continuously
answer three questions: *How much total load is the system carrying? Is
inflow outpacing outflow? Is the current pace sustainable?* Without this,
capacity decisions are made reactively, after strain is already visible.

### What This Delivers

A repeatable analytics pipeline and live dashboard that turns daily raw
counts into five decision-ready signals:

| KPI | What it tells a decision-maker |
|---|---|
| Total Children Under Care | System-wide headcount responsibility, right now |
| Net Intake Pressure | Whether the system is currently gaining or shedding load |
| Care Load Volatility Index | How stable vs. erratic conditions have been recently |
| Backlog Accumulation Rate | Share of recent days showing sustained pressure buildup |
| Discharge Offset Ratio | Whether sponsor-placement throughput is keeping pace with intake |

### Key Takeaway

In modeling the pipeline dynamics, backlog buildup tracks more closely with
**discharge throughput falling behind** than with spikes in raw intake. This
means capacity response should be triggered by the *offset ratio and backlog
streak*, not by headcount alone — those two signals move before total
system load visibly balloons.

### What's Included

- **Research paper** — full EDA, methodology, and findings (`docs/research_paper.md`)
- **Live Streamlit dashboard** — date-range and granularity filters, KPI
  cards, and trend views for ongoing monitoring (`app/app.py`)
- **Reusable data pipeline** — ingestion, validation (with anomaly flagging
  for data-quality transparency), and metric derivation (`src/data_pipeline.py`)

### Recommended Next Step

Point the pipeline at the official published daily series (HHS ORR and CBP
public data) in place of the included placeholder dataset, and stand up the
dashboard for recurring internal review.

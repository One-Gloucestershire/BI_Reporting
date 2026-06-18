# Power BI Usage Report

Greenfield adoption/usage report for the Power BI tenant, sourced from the Power BI
activity-audit feed **`data_mart_l007_icb_powerbi`** on the Redshift reporting cluster
(`ics-glos-reporting`, database `db03_pid_reporting`).

## Model

- **Activity** (fact) — one row per audit event. A single `Value.NativeQuery` partition
  `UNION ALL`s 12 of the `tbl_audit*_201_load` audit tables into a common event grain
  (~154k rows, Sep 2025 → present), deriving `event_type` / `event_category`:
  - View: ViewReport, ViewDashboard
  - Refresh: RefreshDataset
  - Export: ExportReport, DownloadReport, PrintReport, AnalyzeInExcel
  - Share: ShareReport, ShareDataset
  - Create / Edit / Delete: CreateReport, EditReport, DeleteReport
- **Date** (dimension) — DAX calculated `CALENDAR` table, related to `Activity[event_date]`.

Auto date/time (`__PBI_TimeIntelligenceEnabled`) is **off** — the explicit Date table is the
only time dimension.

### Key measures
Active Users, Report Views, Unique Reports Viewed, Refresh Count, Refresh Failures,
Refresh Success Rate, Exports, Shares, New Reports, Report Views PM, Report Views MoM %.

### Pages
Overview (KPIs + trend) · Top Reports & Users · Refreshes · Adoption over time.

## Datashare (resolved 2026-06-18)

The feed lives on the **producer** cluster (`ics-glos-datawarehouse`, `db03_pid`, 103 tables).
It has now been added to the `db03_pid` outbound datashare that surfaces on the reporting
cluster (previously the share only exposed `l005` / `l009` / `l011`):

```sql
-- run on the producer as the share owner (icsuser)
ALTER DATASHARE db03_pid ADD SCHEMA data_mart_l007_icb_powerbi;
ALTER DATASHARE db03_pid ADD ALL TABLES IN SCHEMA data_mart_l007_icb_powerbi;
```

The query is validated end-to-end on the producer (identical engine; 153,743 rows). Consumers
auto-reflect shared objects, so `data_mart_l007_icb_powerbi` is queryable on
`db03_pid_reporting` once the reporting cluster is resumed (it was paused at the time of the
change). This datashare is **not** codified in `data_warehouse` / `AWS_IAC`, so it is managed
directly on the producer rather than via the git → Bytebase path.

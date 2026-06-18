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

## ⚠️ Datashare prerequisite (refresh blocker)

The feed exists on the **producer** cluster (`ics-glos-datawarehouse`, `db03_pid`,
103 tables) but is **not yet exposed through the datashare** that surfaces `db03_pid` on the
reporting cluster — that share currently exposes only `data_mart_l005_icb_activedirectory`,
`data_mart_l009_icb_integratedhub` and `data_mart_l011_chs_continuinghealthcare`.

Until the schema is added to the share, the NativeQuery fails on the reporting cluster with
`Schema data_mart_l007_icb_powerbi does not exist in the database`. The query is otherwise
validated end-to-end on the producer (identical engine; 153,743 rows).

**Action required (producer-side, by the datashare owner / ops):** add the schema to the
outbound datashare feeding the reporting namespace `307662af-…` (consumer DB `db03_pid`):

```sql
ALTER DATASHARE <share_name> ADD SCHEMA data_mart_l007_icb_powerbi;
ALTER DATASHARE <share_name> ADD ALL TABLES IN SCHEMA data_mart_l007_icb_powerbi;
```

This is not codified in `data_warehouse` or `AWS_IAC`, so it is not deployable via the normal
git → Bytebase path — it must be applied by whoever manages the `db03_pid` datashare.

# Reference-data partitions NOT converted (CCG_Reference / DSCRO_NATIONAL_LOOKUPS / ICB_Products)

Generated during the CCG_Reference/DSCRO/ICB_Products reference-conversion pass on the `cloud` branch.
Of 109 target partitions, **42 were converted** to Redshift `Value.NativeQuery` and validated live; the **67 below were flagged** (RS table genuinely missing, source unpopulated/gated, source on a non-migrated DB, or a complex multi-statement/derived query needing semantic sign-off — per the task's convert-single-step / flag-complex rule).

## A. ACG / PLS analytical layer — gated (acgpatientneedsgroup unpopulated in RS)  (10)

RS `data_mart_pls.vw_summary.acgpatientneedsgroup` is entirely NULL (ACG / Johns Hopkins is licence-gated and not populated on the cluster). `REF_PNG` returns 0 rows; ACG aggregates group on a null dimension. **Remediation:** populate the ACG product in `data_mart_pls` (dw + licence), then convert as simple `vw_summary` aliases.

| Report | Partition | On-prem source |
|---|---|---|
| ACG PNG Population Profiles | DAT_Activity | `ICB_Products.Patient.vw_Activity` |
| ACG PNG Population Profiles | DAT_PLS_Summary | `[ICB_Products].[Patient].[vw_Summary]` |
| ACG PNG Population Profiles | REF_PNG | `[ICB_Products].[Patient].[vw_Summary]` |
| ACG Population Profiles v3 | DAT_Activity | `ICB_Products.Patient.vw_Activity` |
| ACG Population Profiles v3 | DAT_PLS_Summary | `[ICB_Products].[Patient].[vw_Summary]` |
| ACG Population Profiles v3 | REF_PNG | `[ICB_Products].[Patient].[vw_Summary]` |
| PHM - Diabetes Predictive Insights Dashboard (NDA + ACG Integrated) | Patient_Summary | `[ICB_Products].[Patient].[vw_Summary]` |
| Population Insights Report | PLS_Activity | `[ICB_Products].[Patient].[vw_Activity]` |
| Population Insights Report | PLS_Summary | `[ICB_Products].[Patient].[vw_Summary]` |
| Primary Care Report | Gloucestershire Patients | `[CCG_Current].[PrimaryCare].[vw_Appointments]` |

## B. IMDCountyDecile absent in data_mart_pls  (2)

`data_mart_pls.vw_summary` and `vw_imd_and_geography` carry `imdnationaldecile` but NOT a county/Gloucestershire decile. **Remediation:** either add the county decile to the PLS mart (dw), or reconstruct in the NativeQuery by `LEFT JOIN ccg_reference.vw_lsoa_imd l ON l.lsoacode = g.lsoacode` and alias `l.derived_imdgloucestershiredecile -> IMD_Gloucester_Decile` (same IMD source; verify parity before shipping). `Patient_Summary` also needs ACG (cat A).

| Report | Partition | On-prem source |
|---|---|---|
| Population Insights Report | PLS_Geography_Primary | `[ICB_Products].[Patient].[vw_IMD_and_Geography]` |
| Population Insights Report | PLS_Geography_Secondary | `[ICB_Products].[Patient].[vw_IMD_and_Geography]` |

## C. RS source table absent  (2)

`DSCRO_NATIONAL_LOOKUPS.Data_Dictionary.Emergency_Care_Department_Type_SCD` has no RS equivalent in `dscro_national_lookups`. It is a ~5-row static lookup (codes 01-05). **Remediation:** add `dd_emergency_care_department_type` to the dscro mart (dw), OR reconstruct as a static `VALUES` NativeQuery once the exact `Main_Description` strings are confirmed from on-prem.

| Report | Partition | On-prem source |
|---|---|---|
| Frailty Report | REF_ED_Department_Type | `[DSCRO_NATIONAL_LOOKUPS].[Data_Dictionary].[Emergency_Care_Department_Type_SCD]` |
| Mental Health Report | REF_ED_Department_Type | `DSCRO_NATIONAL_LOOKUPS.Data_Dictionary.Emergency_Care_Department_Type_SCD` |

## D. Source is a non-reference / non-migrated DB  (1)

The connection DB is a reference DB but the FROM reads a non-migrated table (e.g. `PowerBI_Reporting.dbo.GP_Practice_Ref` with bespoke `Reporting_Locality`/`Reporting_PrimaryCareNetwork`/`ReportingOrganisationName_Adjusted` columns absent from `icb_data_reference.vw_gppractice`). **Remediation:** migrate the underlying PowerBI_Reporting table, or rebuild the adjusted columns in the warehouse.

| Report | Partition | On-prem source |
|---|---|---|
| Mental Health Report | REF_GP_Reference_Table | `PowerBI_Reporting.dbo.GP_Practice_Ref` |

## E. Date dimensions built from non-migrated PowerBI_Reporting/Processing tables  (7)

Date dimension built by selecting from a `PowerBI_Reporting`/`PowerBI_Processing` date table (non-migrated). **Remediation:** repoint to `ccg_reference.vw_datelookup`/`vw_date` if the column set is compatible (per-report column map needed), else migrate the underlying table.

| Report | Partition | On-prem source |
|---|---|---|
| 111 Report | Date Ref | `PowerBI_Reporting.dbo.date_ref` |
| Community Activity Report | REF_Date_Ref | `PowerBI_Reporting.community.tbl02_CSDS_Referrals` |
| GP SMS Messaging Report | REF_DateRef | `PowerBI_Reporting.primarycare.[tbl08_SMS]` |
| Mental Health Report | REF_Date_Ref | `PowerBI_Reporting.mentalhealth.tbl01_MHSDS_MH_Referrals` |
| Personalised Proactive Whiteboard Baselines Report | REF_Date_Ref | `PowerBI_Reporting.AgeingWell.tbl01_Proactive_Whiteboard_Cohort` |
| Prescribing - Dispensing Report | Date Reference | `[PowerBI_Processing].[dbo].[Prescribing_Dispensing_Output]` |
| Respiratory - FeNO & Spirometry Test Indicators Report | Date Reference | `PowerBI_Reporting.Respiratory.tbl01_Respiratory_1a` |

## F. GP Reference — complex multi-statement (#TEMP, practice-merger relabels, coord join)  (15)

Multi-statement T-SQL: `#TEMP` build of a practice-merger relabel (CASE on Locality/PCN/ReportingOrganisationCode/Name) filtered `Commissioner='11M' AND Locality IS NOT NULL`, then a final SELECT, several with a LEFT JOIN to a GP-coordinate table for `GPLatitude`/`GPLongitude`. **Recipe (needs semantic sign-off — relabels drive figures):** rewrite as a single CTE against `icb_data_reference.vw_gppractice` (case-insensitive `commissioner ilike '11m%'`), reproduce each CASE, then `LEFT JOIN data_mart_powerbi_phm.tbl02_demographicsoverview c ON c.gp_practice_code = <reportingorganisationcode>` aliasing `c.gplatitude`/`c.gplongitude` (coords confirmed present in RS).

| Report | Partition | On-prem source |
|---|---|---|
| Cancer Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Creative Health Report - working on | Practice | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Creative Health Report | Practice | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Dementia Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Demographic and Population Analysis Report | GP Reference Table | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Diabetes Report | 8CP & 3TT (National) | `[CCG_Reference].[Diabetes].[vw_NDA_CP_TT]` |
| End of Life Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Health Inequalities Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Integrated Neighbourhood Teams (INT) Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Population Insights Report | Ref_GP_Primary | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Population Insights Report | Ref_GP_Secondary | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Prescribing - Dispensing Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Primary Care Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |
| Respiratory - FeNO & Spirometry Test Indicators Report | GP Reference | `[PowerBI_Reporting].[PHM].[tbl02_DemographicsOverview]` |
| Rockwood Frailty Report | GP Reference | `[CCG_Reference].[Reference].[vw_GPPractice]` |

## G. Date dimensions — complex multi-statement / computed-flag scripts  (25)

Multi-statement date-dimension script (`#TEMP`/CTE + `DENSE_RANK() OVER`, computed reporting-month / SPC / rolling flags, frequently `DECLARE @var`). **Recipe (needs semantic sign-off — reporting flags drive figures):** source `ccg_reference.vw_datelookup` / `vw_date` / `dscro_national_lookups.ref_dates`; translate `EOMONTH->last_day`, `GETDATE()->current_date`, `DATEADD/DATEDIFF/SUBSTRING/DENSE_RANK` 1:1; inline each `DECLARE @x = (SELECT ...)` as a scalar subquery. The CHC `Date` / `Waiting List Date Table` conversions (vw_datelookup LEFT JOIN ref_dates) are a worked template.

| Report | Partition | On-prem source |
|---|---|---|
| Cancer Report | Date Reference | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Contract Monitoring Report | Date Table (First Day of Month) | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Creative Health Report - working on | Date | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Creative Health Report | Date | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Dementia Report | Date Reference | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Dementia Report | Death Date Table | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Demographic and Population Analysis Report | Date Reference Table | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Diabetes Report | a. Date Table | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| End of Life Report | Active Populations - Date Table | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| End of Life Report | Death Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| End of Life Report | PCSP Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| End of Life Report | Palliative Register Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| End of Life Report | ReSPECT Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Frailty Report | REF_Date | `CCG_Reference.Reference.vw_Date` |
| Health Inequalities Report | Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Hospice Activity Report | REF LoS Date Table | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Hospice Activity Report | REF date_table | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Hospice Activity Report | REF date_table (2) | `[CCG_Reference].[Reference].[vw_DateLookup]` |
| Integrated Neighbourhood Teams (INT) Report | Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Primary Care Report | Date Reference Script | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Rockwood Frailty Report | Date Reference | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Urgent Care Report | Date Table | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Virtual Wards Report | 06 H@H Date Table | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Weight Management Report | Date Table (all dates) | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |
| Weight Management Report | Date table (month start) | `[DSCRO_NATIONAL_LOOKUPS].[dbo].[ref_Dates]` |

## H. Other complex multi-join / derived queries  (5)

Complex multi-join / derived (e.g. national NDA 8CP&3TT, prescribing population builds, `vw_GPPracticePopulation` whose RS home is unconfirmed). **Remediation:** port per-query against the relevant data_mart with validation; confirm RS source first.

| Report | Partition | On-prem source |
|---|---|---|
| Community Activity Report | REF_EFI | `PowerBI_Reporting.Frailty.tbl01_Frail_Patient_Deficits` |
| Diabetes Report | Ref. Age Reference | `SSMS` |
| Frailty Report | REF_LSOA | `CCG_Reference.Reference.vw_LSOA_IMD` |
| Personalised Proactive Whiteboard Baselines Report | GP Practice Populations | `CCG_Reference.Reference.vw_GPPracticePopulation` |
| Personalised Proactive Whiteboard Baselines Report | REF_LSOA | `CCG_Reference.Reference.vw_LSOA_IMD` |

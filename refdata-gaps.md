# Reference-data partitions NOT converted (CCG_Reference / DSCRO_NATIONAL_LOOKUPS / ICB_Products)

Generated during the CCG_Reference/DSCRO/ICB_Products reference-conversion pass on the `cloud` branch.
Of 109 target partitions, **42 were converted** to Redshift `Value.NativeQuery` and validated live; the **67 below were flagged** (RS table genuinely missing, source unpopulated/gated, source on a non-migrated DB, or a complex multi-statement/derived query needing semantic sign-off — per the task's convert-single-step / flag-complex rule).

---
## UPDATE 2026-06-24c — CCG_Current / leftover-target-DB pass (3 converted, 7 flagged)

A targeted pass over the remaining Population Insights (ICB_Products), Circulatory/Diabetes/Whiteboard
(CCG_Reference), and EoL/Primary Care/Virtual Wards/Creative-Health-working-on (CCG_Current) partitions.
**3 converted (live-tested, validate_phm_repo OK), 7 flagged.** (WM's CCG_Current partition already 0 left.)

CONVERTED:
- **End of Life / ReSPECT Plans Coded** — on-prem `CCG_Current.PrimaryCare.vw_Events` is an LBV that
  FAILS on the consumer (cross-db ref). Sourced the **non-LBV base table**
  `data_mart_primarycare.tbl_event_201_load` instead (pseudonhsnumber/eventdate/snomedcode present).
  43,926 rows / 23,234 patients vs on-prem 44,457 / 23,449 (98.8% — base-table is the only viable path).
- **Virtual Wards / 08 Readmissions** — the partition is a **commented-out stub** (`SELECT [Readmission_date_only]=''`
  only; the real `CCG_Current.GHFT.vw_IPVirtualWard` logic is all `--`). Faithfully reproduced as
  `select cast('' as varchar) as "Readmission_date_only"` (1 row). No table needed.
- **Circulatory / 4. Hypertension** — fact `select * + [Latest YearEnd]` from
  `data_mart_powerbi_circulatory.tbl04_hypertensioncohorts`; all 57 model cols present (RS +1 imdnationaldecile),
  `[Latest YearEnd]` already precomputed in the RS mart so no subquery. **EXACT**: 6,475,001 rows /
  Latest-YearEnd 382,885 == on-prem.

FLAGGED (genuine blockers — no RS home / LBV / gated):
- **PopIns PLS_Activity / Dat_Bed_Days / Dat_Patient_Weighting** — read `ICB_Products.Patient.vw_Activity`;
  **no `data_mart_pls.vw_activity` in RS** (`Relation vw_activity does not exist`). dw must migrate the PLS
  activity feed. (Dat_* are also multi-stage #TEMP.)
- **PopIns PLS_Summary** — selects `[PLS].[ACGPatientNeedsGroup]` + ACG product fields; `acgpatientneedsgroup`
  100% NULL. ACG-gated (licence + dw).
- **Diabetes / 8CP & 3TT (National)** — `CCG_Reference.Diabetes.vw_NDA_CP_TT` has no RS home.
- **Whiteboard / GP Practice Populations** — `CCG_Reference.Reference.vw_GPPracticePopulation` has no RS home.
- **Primary Care / Gloucestershire Patients** — spine is `CCG_Reference.Population.vw_PDS_Current` (no
  RS PDS-current home — only data_mart_n011_csu_pds MPI tables, different shape) AND the appointments leg
  uses the `vw_appointments` LBV (same cross-db failure). Needs a PDS-current mart in RS.
- **Creative Health Report - working on / Outcome measures** — 305-line `#TEMP_CH_Fixed` ISNUMERIC cleaning
  over `CCG_Current.CreativeHealth.vw_CreativeHealthConsortium` (uncertain RS home; no RS `ISNUMERIC`).
  Bespoke — defer (the *live* Creative Health report's Outcome measures already sources the community mart).

NOTE — the `vw_events` / `vw_appointments` LBVs in `data_mart_primarycare` both throw
`cross-database reference to db01_reference.icb_data_reference.vw_gppractice ... while analyzing an LBV on
producer`. Where a base `tbl_*_201_load` exists (events), source that directly; where the spine itself is
the LBV/absent (appointments cohort), it stays blocked.

---
## UPDATE 2026-06-24 — second reference-DB pass (53 of the flagged-67 now CONVERTED)

A follow-up pass cleared the tractable date-dimension (cat G), GP-reference (cat F), and small
B/C/H buckets. **53 partitions converted, live-tested on `ics-glos-reporting`, validate_phm_repo OK,
pushed to `cloud`** (commits `8a38b07` Frailty + `590541d` the 24-report batch):

- **Cat C (ED Department Type) ×2** — no RS `dd_emergency_care_department_type`; reconstructed as a
  static `UNION ALL` of the 5 on-prem rows (Main_Description pulled from on-prem). Frailty + MH. EXACT.
- **Cat G date dims ×30** — repointed to `dscro_national_lookups.ref_dates` / `ccg_reference.vw_date`
  / `vw_datelookup`; @vars/#TEMP inlined as scalar subqueries (EOMONTH→last_day, GETDATE→current_date,
  CONVERT(,103)→to_char DD/MM/YYYY, DENSE_RANK 1:1). Frailty REF_Date, Cancer, Dementia ×2, EoL ×5,
  Hospice ×3, Contract Monitoring, Creative Health ×2, Demographic, Diabetes, Health Inequalities, INT,
  Primary Care, Rockwood, Urgent Care, Virtual Wards, WM ×2, Community, GP SMS, MH, Whiteboard, Planned Care.
  All row-count == on-prem EXACT (one exception: Community REF_Date_Ref 1491 vs 1522 = fact-table
  freshness lag in `data_mart_powerbi_community.tbl02_csds_referrals`, logic faithful).
  GOTCHAS propagated: on-prem `@@DATEFIRST=1` Monday-based weekday → RS `((extract(dow)+6)%7)+1`;
  `vw_datelookup.financialmonth` is VARCHAR (must `cast(... as int)` for `<=`); `vw_date.financial_month`
  is INT.
- **Cat F GP refs ×15** — single CTE on `icb_data_reference.vw_gppractice` (`commissioner ilike '11m%'`),
  relabel CASEs reproduced, coords via LEFT JOIN `data_mart_powerbi_phm.tbl02_demographicsoverview`.
  Counts == on-prem (standard 87 / Cancer 86 / Respiratory 86). Cancer/Dementia/EoL/PrimaryCare/WM/
  PopIns(Primary+Secondary)/HI/INT/Demographic/Prescribing/Rockwood/Respiratory-FeNO/CreativeHealth×2.
- **Cat B (IMD county decile) ×2** — Population Insights PLS_Geography Primary+Secondary: repointed
  `data_mart_pls.vw_imd_and_geography` + LEFT JOIN `ccg_reference.vw_lsoa_imd` for the absent
  IMD_Gloucester_Decile (`derived_imdgloucestershiredecile`). 720,794 rows, 90% with Glos decile.
- **Cat H (LSOA) ×2 + Diabetes Ref.Age + HI Ethnicity** — Frailty/Whiteboard REF_LSOA = vw_lsoa_imd +
  vw_geographymapping (32,844 / 373 Glos); Diabetes Ref.Age = `ccg_reference.vw_ageband` (131 rows);
  HI Ethnicity = `data_mart_pls.vw_ethnicity.derivedethnicitygroup` (6 == on-prem).

### GP-reference map coordinates — FIXED (repointed off the NULL demographicsoverview)
The cat-F coord join originally targeted `data_mart_powerbi_phm.tbl02_demographicsoverview`, but
**that table's gplatitude/gplongitude are 100% NULL in RS** (0/720,794). **Fixed** (commits up to
`e249f2e`): repointed the inner coord subquery in all 14 coord-joining GP-refs to
`data_mart_primarycare.tbl01_gp_practice_populations`, with a **de-swap** — that table's columns are
transposed (`gp_latitude` holds the longitude value, `gp_longitude` holds the latitude value),
verified vs on-prem L84003 (51.901639 / -2.0893682). Mapping: `gp_longitude → GPLatitude`,
`gp_latitude → GPLongitude`. Live-validated: GPLatitude 51.6–52.1, GPLongitude −1.7 to −2.5, 85/87
practices populated (63 distinct Glos practices have coords; closed/historic don't, faithfully). Maps
now render. (If dw later back-fills demographicsoverview coords, either source is fine.)
The 14: Dementia, Demographic, EoL, Health Inequalities, INT, PopIns Ref_GP_Primary+Secondary,
Prescribing, Primary Care, Rockwood, Respiratory-FeNO, Creative Health ×2, WM R.GP Ref.

### STILL FLAGGED after this pass (genuine blockers)
- **Cat A ACG/PNG — STILL GATED (×7).** Re-verified `data_mart_pls.vw_summary.acgpatientneedsgroup`
  = 100% NULL (0/720,794). REF_PNG / DAT_ADG / DAT_PLS_Summary (ACG ×2 reports), PHM-Diabetes
  Patient_Summary, PopIns PLS_Summary (selects `[PLS].[ACGPatientNeedsGroup]` + `[ACG].chronic_condition_*`).
  Needs ACG product populated (licence + dw).
- **PLS *activity* mart absent (×3+).** PopIns PLS_Activity / Dat_Bed_Days / Dat_Patient_Weighting and
  the ACG reports' DAT_Activity all read `ICB_Products.Patient.vw_Activity` (+ vw_Activity_Summary) —
  there is **no `data_mart_pls.vw_activity` in RS** (`Relation vw_activity does not exist`). Needs the
  PLS activity feed migrated (dw). (Dat_Bed_Days/Dat_Patient_Weighting are also multi-stage #TEMP.)
- **WM `Ref - Source Table` / `Population` / `Refresh Date` — NOW CONVERTED** (commit `2aa6150`).
  Sourced `data_mart_pls.vw_summary` (+vw_imd_and_geography). Patient parity is exact (RS 11M 698,100
  vs on-prem 697,892); Population 675,878 vs 675,592 (100.04%, 393 LSOA×district groups identical). The
  earlier ~86% distinct-combo figure was column-cardinality cosmetic, not missing patients. Glos-11M
  only (on-prem also reads QR1, absent in RS — negligible for a Glos report).
- **Whiteboard `GP Practice Populations`** — on-prem `CCG_Reference.Reference.vw_GPPracticePopulation`
  (CENSUSDATE 'MMM-YY', AgeGroupType, SELECT *) has NO RS equivalent of that shape. FLAG (dw build).
- **Diabetes `8CP & 3TT (National)`** — on-prem `CCG_Reference.Diabetes.vw_NDA_CP_TT` (national NDA
  care-processes audit) has NO RS home (`svv_redshift_tables` empty for nda_cp_tt). FLAG (dw ingest).
- **WM `Ref - Source Table` / `Population` / `Refresh Date`** — translate cleanly against
  `data_mart_pls.vw_summary` (logic verified, queries run), BUT the RS PLS mart is **Glos-11M only (no
  QR1) and ~14% fewer distinct 11M demographic combos than on-prem** (39,105 vs 45,358). Held back to
  avoid shipping a ~86%-parity demographic slicer. Convert once `data_mart_pls` reaches on-prem parity.
- **Out-of-lane (primary FROM a non-target fact DB; belong to other migration lanes):** Contract
  Monitoring PLCM family (BIReports/PowerBI), Circulatory Hypertension/Heart Failure, Primary Care
  appointments (BIReports/CCG_Current), Creative Health "working on" #TEMP draft, EoL/HI Census
  Population, Hospice hospice_at_home_quarterly, UC LSOA Populations, VW 08 Readmissions, etc.

**Net repo state after this pass: 72 `Sql.Database` partitions remain (down from 149).** The original
67-flagged list below is superseded for the converted rows; the remaining blockers are summarised above.

---

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

# BI_Reporting (Live Branch Deep-Dive)

This repository stores **Microsoft Fabric / Power BI artifacts as source files**.
It is not an app/service codebase; it is a catalogue of report definitions (`*.Report`) and semantic models (`*.SemanticModel`).

## Scope

This README is intentionally focused on the **`live` branch content only**.

## What is in the live branch

- 47 active report folders (`<Name>.Report`)
- 47 matching semantic model folders (`<Name>.SemanticModel`)
- archived/retired content under `01 Archive/`

Each live report follows a paired structure:

- `<Name>.Report` → pages, visuals, bookmarks, themes, custom visuals, static assets
- `<Name>.SemanticModel` → tables, relationships, measures, Power Query expressions, cultures

## Key technologies and file formats

- **PBIR** (`definition.pbir`, `report.json`) for report metadata/layout
- **PBISM** (`definition.pbism`) for semantic model item metadata
- **TMDL** (`definition/*.tmdl`) for model internals (tables, relationships, expressions)
- **Power Query M** in `definition/expressions.tmdl`
- **Power BI custom visuals** packaged under `CustomVisuals/` in some reports

## How the codebase is organized

For each subject area, you normally work in a pair:

1. Open `<Subject>.Report/report.json` to inspect pages, visuals, filters, bookmarks, and resources.
2. Open `<Subject>.SemanticModel/definition/model.tmdl` to see model table references.
3. Open `<Subject>.SemanticModel/definition/tables/*.tmdl` for columns/measures.
4. Open `<Subject>.SemanticModel/definition/expressions.tmdl` for query logic and source steps.
5. Open `<Subject>.SemanticModel/definition/relationships.tmdl` for model joins.

## Report-by-report guide (live branch)

The list below is based on reading `report.json`, `definition/model.tmdl`, and semantic-model metadata for each live report pair.

- **111 Report** — Pages: 111 Validations and Redirections, 111 Call Activity | Core model tables: 111 Data, Disposition Group (PPG) Dynamic Table, Validations/Redirect Dynamic Table
- **ACG PNG Population Profiles** — Pages: 09, 08, 06, 11 | Core model tables: DAT_PLS_Summary, DAT_ADG, DAT_ACG, DAT_Activity, DAT_ASC_Service
- **ACG Population Profiles v3** — Pages: 09, 08, 06, 11 | Core model tables: DAT_PLS_Summary, DAT_ADG, DAT_ACG, DAT_Activity, DAT_ASC_Service
- **Cancer Report** — Pages: Referrals & Treatments, Diagnosis, Referrals vs Treatments, All 2WW | Core model tables: 2WW Referrals, GP Reference, Referrals & Treatments, MPI, Admissions | Bookmarks/views: Time Series with Legend, ICB Comparison Time Series, Time Series
- **Cancer Wait Times Report** — Pages: 104 day summary info, 28 Day, Cancer Backlog, Summary | Core model tables: two_week_wait, 104_day, 28_day, 31_day, 62_day
- **Cinapsis Report** — Pages: Cinapis Urgent Care Activity, Cinapis Urgent Care Outcomes, Cinapis Planned Care Activity | Core model tables: Call Activity, Case Activity, Service Dimension, OrganisationGroup Dimension
- **Circulatory Report** — Pages: Secondary Care Explorer, Project Level Metrics, Programme Level Metrics, Heart Failure | Core model tables: 1. Programme Level Metrics, 2. Project Level Metrics, Populations, 5. Community Refs, Metric Definitions | Custom visuals: 2
- **Community Activity Report** — Pages: Moderate & Severe_Frailty_Used_Frailty_Oversight_board_29/04/2026, Used_CC@H_Evaluation_2025, Contacts, Referrals & Discharges | Core model tables: 1 - Community_Referrals, 2 - Contacts, 3 - Community Hospital Admissons, Parameter_Community_Hospital_metrics, Parameter - Locality/PCN/Practice | Bookmarks/views: Referrals over time, Referrals by source
- **Continuing Healthcare Report** — Pages: Fast Track Page, reviews, Summary Metrics, What is CHC? | Core model tables: 28_days, PHB, One_time_cost, Front_page, CHC_application
- **Contract Monitoring Report** — Pages: Detail Table, EBI Activity, Elective Spend, CDC Activity | Core model tables: PLCM Data, Aggregate Data, IAPs, Ref. Organisation Reference, Ref. POD Reference
- **Creative Health Report - working on** — Pages: Service Usage, Mindsong, Referrals, Cohort Analysis | Core model tables: CH cohort data, Population cohort, Practice, Age Reference, Gender Reference
- **Creative Health Report** — Pages: Service Usage, Mindsong, Referrals, Cohort Analysis | Core model tables: CH cohort data, Population cohort, Practice, Age Reference, Gender Reference
- **Dementia Report** — Pages: Alzheimer Society, Demographics, More MAS, Practice DDR | Core model tables: Practice Dementia, Practice Population, GP Reference, Dementia Cohort, Query1 | Bookmarks/views: Gloucestershire DDR, No area selected DDR, Demographics - Care Home | Custom visuals: 4
- **Demographic and Population Analysis Report** — Pages: Emergency Department Overview, Outpatient Overview, Primary Care Overview, Elective Admission Overview | Core model tables: Population Overview, Health Overview, Population, Comorbidities, PyramidParameter | Bookmarks/views: Total Numbers, Crude Rate, Age Standardised | Custom visuals: 3
- **Diabetes Report** — Pages: NATIONAL -  8 Care Processes & 3 Treatment Targets, LOCAL - 8 Care Processes, Highlights | Core model tables: Ref. GP Practice Reference, Ref. Age Reference, 8CP & 3TT (Local), NDA Local Performance, 8CP & 3TT (National) | Custom visuals: 5
- **Diagnostic Monitoring Report** — Pages: CDC, Summary, Breaches, Test Report Disclaimer | Core model tables: Diagnostic, Button | Bookmarks/views: GHT - Summary, ICB - Summary, GHT Breaches | Custom visuals: 1
- **Dynamic Support Register Mapping Report** — Pages: Mapping | Core model tables: Sheet1, Query1
- **End of Life Report** — Pages: Cause of Death, Sandbox, Mortality Overview - Rate, ReSPECT Plans | Core model tables: EoL Data, GP Reference, Population, Gender Reference, LTC Reference Table - ALL | Bookmarks/views: PCN & Practice View - Deaths, PCN & Practice View - Palliative Care | Custom visuals: 1
- **Falls Report** — Pages: PC, ED Coding, Falls ED Attendances, Falls SWAST | Core model tables: ED Falls (GHFT Only), Place Population, Admissions Falls, Hour of day, Dementia population | Bookmarks/views: Non-YTD SWAST Identifiable, YTD Admissions, Non-YTD Admissions | Custom visuals: 2
- **Frailty Report** — Pages: ED attendances split by frailty, Frailty Over Time, ED Attendances, Emergency Plot the dots test | Core model tables: 3.cinapsis_frailty_assessment, 2.emergency_admissions, 1.ed_attendances | Custom visuals: 1
- **GP SMS Messaging Report** — Pages: Build and refresh notes, GP Practice View, Report Guide and Navigation, Total and PCN View | Core model tables: RAW_Fragment cost, RAW_Fragments&Characters, vw_SMS_Activity, GP Practice Populations | Custom visuals: 1
- **Health Inequalities Report** — Pages: Metrics Explorer, Metrics Explorer - No Comparison, Metric Metadata, Exportable Page | Core model tables: GP Reference, Metrics Table, Ethnicity Reference, Deprivation Reference, Census Population - Gloucestershire
- **Hospice Activity Report** — Pages: Average, Monthly and daily hours, Hospice at Home, H@H Rate | Core model tables: H@H monthly SP, hospice_at_home_quarterly, Patient Carer services SP, Inpatient Unit SP, H@H quarterly care hours SP | Custom visuals: 1
- **ICB Report v2** — Pages: Mental Health Talking Therapy, Mental Health - Adults, LD & Autism, Community Care & Ageing Well | Core model tables: Merge - Main SQL _ Population, TimeSeries - Merged, MainDataset_SQL, Benchmarking Data, Manual Metrics | Bookmarks/views: S001a, Online Consultations, Dental Activity | Custom visuals: 2
- **ICB Report** — Pages: Mental Health Talking Therapy, Mental Health - Adults, LD & Autism, Community Care & Ageing Well | Core model tables: Merge - Main SQL _ Population, TimeSeries - Merged, MainDataset_SQL, Benchmarking Data, Manual Metrics | Bookmarks/views: S001a, Online Consultations, Dental Activity | Custom visuals: 2
- **Integrated Neighbourhood Teams (INT) Report** — Pages: INT Metrics, Definitions | Core model tables: GP Reference, GP Populations, INT Metric Population, PC&SP Events, ReSPECT Events
- **Learning Disabilities and Autism Report** — Pages: Tooltip IMD England, Acute Care: IP, DC, OP, Acute Care: ED, Prescribing | Core model tables: Pop Dems, AHC, HAP, IP and Daycases - over time, OP_over time | Bookmarks/views: Bookmark 1 R, Bookmark 2 A | Custom visuals: 4
- **MSK Report** — Pages: 2 Improve Management, 1 Timely Access | Core model tables: GP Table, Outpatient_MSK, Triage_Outcome, Emergency MSK Admissions, A&E | Custom visuals: 1
- **Maternity Report** — Pages: Pregnancies, Deliveries, Births | Core model tables: Pregnancies, Deliveries, Births | Custom visuals: 5
- **Mental Health Report** — Pages: MH UEC - ED Attendances, MH UEC - Acute Admissions, MH KPIs, Contacts | Core model tables: 1.Community_Referrals, 2.Community_Discharges, 3.Inpatient Admissions, 4.Inpatient Discharges, 8.CYP_Access_Rates
- **Non-Emergency Patient Transport Services Report** — Pages: KPIs, Tooltips 1, Pop Dems Actuals, KPI Detail | Core model tables: Main_Journeys, GHT_OntheDay, Target_upload, Contracted Activity, Dialysis Distinct Patients | Custom visuals: 4
- **PHM - Diabetes Predictive Insights Dashboard (NDA + ACG Integrated)** — Pages: Predictive, Descriptive, SQL Python Explanation, Reports | Core model tables: GP Practice Reference, TrajectoryAnalysis, Patient_Summary, Patient_Summary_Unpivoted, LTC_Conditions
- **Personalised Proactive Whiteboard Baselines Report** — Pages: Drill Through Page - All Other Metrics, PPW Baseline Monitoring, Background & FAQs, Drill Through Page - Page 2 | Core model tables: 1.Baselines, GP Practice Populations, Total on whitebaord - Rolling 3-Month Average, Total proportion of PPW died in their preferred place of death - Rolling 3-Month Average | Bookmarks/views: 1.Go to Total registered population (60+) on the whiteboard, 2.Go to Proportion on the whiteboard with a palliative care code recorded, 3.ResPECT plan recorded
- **Planned Care Report** — Pages: Referral Assessment Service, Referrals, Outpatients, Electives | Core model tables: electives, outpatients, Practice Populations, Outpatient Parameter, E-Referrals | Bookmarks/views: Initial Referrals, Bookings, Referral Rejections | Custom visuals: 1
- **Population Insights Report** — Pages: Gloucester Profile, Long Term Conditions, Navigation Page, Cohort Comparison | Core model tables: PLS_Summary, PLS_Ethnicity, PLS_Geography_Primary, PLS_Activity, Par_Activity_Switch | Custom visuals: 2
- **Prescribing - Dispensing Report** — Pages: Age Standardised Rates, Demographics Page, Summary, Tool Tip Page | Core model tables: GP Population, GP Reference, Gender Reference, Ethnicity Reference, Dispensing Data | Custom visuals: 3
- **Prescribing Report** — Pages: Over the Counter, Do not prescribe, Practice Variation, Top Items and Costs | Core model tables: EPACT, Population, Quartiles, PracticeLevel, BNFReference | Bookmarks/views: Trends Rate, Trends Actual Cost, Variation Rate | Custom visuals: 2
- **Primary Care Report** — Pages: Clinically Urgent Appointments, Quality Performance, % Appointment Categories - Local Picture, Growth | Core model tables: GP Population, Reference Population, GP Reference, Age Band Reference, Gender Reference | Custom visuals: 3
- **Proactive Care Cohort Report** — Pages: Front Sheet, Maps, Cohort Analysis | Core model tables: proactive_care_cohorts, practice_populations, locality_populations, pcn_populations, ward_populations
- **Referral To Treatment Report** — Pages: ICB, OOC & Independent, GHT, Benchmarking | Core model tables: RTT, Benchmarking, Provider Reference, Unpivoted RTT, Part Description Reference | Custom visuals: 3
- **Report Navigation Page** — Pages: Report Navigation Page | Core model tables: Report List
- **Respiratory - FeNO & Spirometry Test Indicators Report** — Pages: 3. FeNO/Spiro patient count, Asthma metrics, Metric Index, Metrics Data | Core model tables: Age Band Reference, GP Reference, Ethnicity Reference, Metric Data Table, Metric Index | Custom visuals: 3
- **Respiratory Report** — Pages: Nebuliser Data, Primary Care, A&E, Pulmonary Rehab | Core model tables: PulmonaryRehab_data, Acute_Admissions, New Primary Care Diag, GP Table, New Annual Reviews
- **Rockwood Frailty Report** — Pages: Frailty over Time, Frailty Metrics - Non-Frail Included, Mapping, Frailty Metrics | Core model tables: GP Population, Reference Population, GP Reference, Age Band Reference, FY Reference
- **Urgent Care Report** — Pages: Admissions, A&E/MIIU, SWASFT, Duplicate of Admissions | Core model tables: 3. Admissions, 2. A&E. Patient level data, Latest Refresh, Weekday Reference, 1. Ambulance. SWASFT - Performance | Custom visuals: 5
- **Virtual Wards Report** — Pages: Discharges, Admissions, Hospital @ Home | Core model tables: 03 Discharge, 05 Hospital @ Home, 01 Admissions, 07 H@H Virtual Wards only, 08 Readmissions | Bookmarks/views: ALL wards - Admissions, Individual wards - Admissions, ALL wards - Discharges
- **Weight Management Report** — Pages: BMI Distribution, Cohort 2, Prescribing 2, Tiers | Core model tables: Population, Tier 3/4, Cohort Analysis, Tier 2, Prescrbing (patient level) | Bookmarks/views: Adj_BMI_Graph, Dist_BMI_Graph | Custom visuals: 5

## Archive (`01 Archive`)

`01 Archive` contains older or superseded report/model pairs in the same file format.
Treat these as historical reference unless explicitly reactivated.

## Practical contributor workflow

1. Pick the report/model pair you are changing.
2. Confirm report-to-model linkage in `definition.pbir`.
3. Review/modify model logic in semantic model TMDL files.
4. Review visual/page behavior in `report.json`.
5. Keep changes isolated to the intended report pair unless doing shared refactoring.

## Glossary

- **PBIR**: Power BI report item definition format.
- **PBISM**: Power BI semantic model item metadata format.
- **TMDL**: Tabular Model Definition Language used for semantic model source control.

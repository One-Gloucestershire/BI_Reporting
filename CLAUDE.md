# CLAUDE.md — working on the Gloucestershire Population Health Power BI report

Hard-won lessons for editing this PBIP/PBIR project (TMDL semantic model + PBIR
enhanced report format) as **source files**, deploying via **Fabric git
integration** on the `cloud` branch, and opening in **Power BI Desktop**.

Run `python tools/validate_phm_repo.py` before every commit. But know its
limits — see "Three different validators" below.

---

## 0. Three different validators — passing one ≠ passing the others

A change can pass our script, deploy fine to the Service, yet **fail to open in
Desktop** (or vice-versa). They enforce different rules:

| Layer | Strictness | Catches |
|---|---|---|
| `tools/validate_phm_repo.py` | lightest | unresolved field refs, BOM, bad colour literals |
| **Fabric Service** import (git Update) | medium | invalid report JSON (missing `queryRef`), broken M |
| **Power BI Desktop** (full AS engine) | strictest | measure/column name collisions, duplicate measure names |

**Before committing, also run these Desktop-only checks** (not yet in the
script — add them):
- no measure shares a name (case-insensitive) with **any** column, model-wide
- no two measures share a name (measures are global)

---

## 1. Measure / column name collisions = "cannot be created because a column with the same name already exists" (`PFE_XL_MEASURE_COLUMN_ALREADY_EXIST`)

Power BI Desktop's modelling engine **rejects a measure whose name matches any
column anywhere in the model** (case-insensitive, model-wide — not just same
table). The Fabric Service import is lenient, so these stay latent until someone
opens the PBIP in Desktop. We were bitten twice:
- `Deaths` measure vs a `deaths` column
- `Patients` measure vs `patients` columns in 8 tables

**Fix:** rename whichever is less referenced. Renaming a *column* (keep its
`sourceColumn`) is safest when it has no visual references — pure TMDL, no
visual edits, data unchanged. Renaming a *measure* means updating every
`queryRef`/`nativeQueryRef` in the visuals too (see §3).

**Avoid generic measure names** (`Deaths`, `Patients`, `Population`) — they
collide with raw count columns. Prefix them (`EoL Deaths`, `Mortality Deaths`).

---

## 2. Cross-database connection pattern (Redshift datashare)

Model tables connect to **`db02_nopid`** and **cross-query `db03_pid`** via a
3-part name, e.g.:
```
Value.NativeQuery(AmazonRedshift.Database("ics-glos-reporting...:5444","db02_nopid"),
  "select ... from db03_pid.data_mart_l050_phm_rpt.<table>", null, [EnableFolding=true])
```
Connecting **directly** to the `db03_pid` datashare DB refreshes **empty**.

New `data_mart_l050_phm_rpt` tables must be **added to the `db03_pid` datashare
per-table** (superuser-only `ALTER DATASHARE db03_pid ADD TABLE ...`, run with
the icsuser managed secret) or they're invisible on the reporting cluster —
`validate`/Desktop won't warn you; the visual just shows nothing after refresh.

---

## 2a. Bulk-converting on-prem `Sql.Database` partitions → Redshift `Value.NativeQuery`

When repointing a report's data source from on-prem MSSQL to the reporting
cluster, you rewrite each table's `partition … = m` source. Pitfalls that each
cost a failed Fabric import:

- **Match the WHOLE `Sql.Database(...)` call.** A non-greedy regex like
  `Sql\.Database\(.*?\]\)` stops at the **first `])`** — which for any bespoke
  query containing `MAX([col])` / `[x])` is **inside the original T-SQL**, not the
  call's end. It leaves a dangling T-SQL fragment after your `Value.NativeQuery`,
  and Fabric import dies: **`M Engine error: Token ',' expected`**. Use a
  query-string-aware pattern, e.g.
  `Sql\.Database\([^[]*\[Query="(?:[^"]|"")*"[^\]]*\]\)` (also handles
  `, CommandTimeout=…`). This bit the Virtual Wards date tables.
- **A well-formed `Value.NativeQuery(...)` always ends `…[EnableFolding=true])`
  immediately followed by `,` or a newline.** Anything else = corruption.
  `validate_phm_repo.py` check 7 now flags this repo-wide — run it after any
  conversion.
- **Escape `"` as `""`** inside the M query string. Odd `"` counts ⇒ unterminated
  string ⇒ same `Token ',' expected`. (check 7 also flags odd quote counts.)
- **Redshift lowercases identifiers.** Alias every column back to the casing the
  model's `sourceColumn` expects (`died_in_hospital_flag as "Died in hospital flag"`).
  This only survives because the **reporting cluster has
  `enable_case_sensitive_identifier=true`** (param group `ccg-reporting-group`,
  reporting cluster only — *not* the shared `ccg-group`). Double-quote any RS
  identifier that isn't a safe bare token (digit-leading / `-` `+` space).
- **Reusable sources:** the date dimension lives at `ccg_reference.vw_date`
  (snake_case) / `ccg_reference.vw_datelookup` (mixed-case `DateKey…`); GP ref =
  `icb_data_reference.vw_gppractice`; populations = `data_mart_primarycare.tbl01_gp_practice_populations`.
  Always **read the original `[Query=…]`** — most "Date"/"GP"/"ref" partitions are
  bespoke aliased `SELECT`s (or temp-table scripts), not `select *`.

---

## 3. PBIR visual field references need `queryRef` AND `nativeQueryRef`

A projection is not just `{ "field": {...} }`. Every measure/column reference
needs all three keys, or Fabric rejects the **whole report** import with
`Report_Import_FailedToImportReport` (and leaves the workspace in a conflict):
```json
{ "field": { "Measure": { "Expression": {"SourceRef": {"Entity": "Targets"}},
                          "Property": "Achievement (% of Target)" } },
  "queryRef": "Targets.Achievement (% of Target)",
  "nativeQueryRef": "Achievement (% of Target)" }
```
When you repoint a visual to a new/renamed measure, update `queryRef`
(`Table.Measure`) and `nativeQueryRef` (`Measure`) too — and any
`sortDefinition` that referenced the old field.

---

## 4. Titles, colours, layout (PBIR rendering)

- **Titles** render from `visualContainerObjects.title`, *not* `objects.title`.
  `finalize_phm.py` copies one to the other — run it after generating pages.
- **Colour literals** must be single-quote-wrapped inside the expr: `"'#005EB8'"`.
  A bare `"#005EB8"` blanks the **entire canvas**. `validate_phm_repo.py` guards this.
- No local render here — **layout/truncation changes can't be verified from
  source**. Verify in Desktop or on the deployed report; don't blind-edit
  positions on the live report.

---

## 5. TMDL gotchas

- A measure/column name with a space (or any non-identifier char) must be
  **single-quoted**: `measure 'EoL Deaths' = ...`. Reference it as `[EoL Deaths]`.
- An **apostrophe inside** a quoted name breaks the identifier — avoid `'` in
  friendly names (`Ethnicity (mother)`, not `Mother's ethnicity`).
- `lineageTag`s should be unique. When adding tables/measures, give fresh tags.
- The JSON/TMDL are the **source of truth** (hand-edited beyond what the
  generators produce). **Never regenerate the whole model/report** — you'll wipe
  manual fixes. Edit in place or emit additively, then `finalize_phm.py`.
- Register every new table in `model.tmdl`: add to the `PBI_QueryOrder`
  annotation array **and** add a `ref table X` line.

---

## 6. Deploy flow (Fabric git integration on `cloud`)

1. Commit + push source to `cloud`.
2. Workspace → **Source control → Update all** (deploys model + report definition).
   - "Update all" aborts at the **first failing item** (alphabetical, no
     per-item update) — one broken semantic model silently blocks all
     later reports.
   - A report-import failure leaves a **conflict** → **Resolve conflicts →
     Accept incoming changes** (git is source of truth), tick the
     acknowledgement, **Merge And Update**.
3. **git Update does NOT refresh data.** New/changed import tables stay blank
   until a **manual or scheduled refresh**. After deploying a model query
   change (e.g. fixing a source column), trigger **Refresh now** and wait for it
   to finish before checking visuals.

---

## 7. Data-correctness traps (not report bugs, but they look like them)

- A measure showing **"(Blank)"** is often the NativeQuery aliasing the **wrong
  or empty source column** (e.g. RTT aliased the empty `total` instead of
  `total_all`). Verify the source column is *populated* in Redshift, not just
  that the query parses.
- **Ratio indicators on a shared count/% axis flatten to nothing** — normalise
  to "% of target" (`value / target`) so every bar is comparable.
- **Aggregate rows** (`Total`, `TOTAL`, `Persons`, `delete` junk statuses) leak
  into part-to-whole charts — filter them at source or with a visual-level filter.

---

## 8. This repo has MANY worktrees / clones — know which one you're in

`C:\BI_Reporting`, `C:\BI_Reporting_cloud`, `…_phm`, `…_cred`, `…-nhs`, etc. are
**git worktrees of the same repo**. Consequences:
- A branch (e.g. `cloud`) can only be checked out in **one** worktree at a time
  (`fatal: 'cloud' is already used by worktree at ...`). To put another worktree
  on the latest cloud content, create a tracking branch: `git checkout -B
  <name> origin/cloud`.
- If Desktop shows an error you already fixed, you're almost certainly opening a
  **different worktree** on a **stale branch**. Check `git -C <dir> branch
  --show-current` and `git -C <dir> log --oneline -1` before debugging the file.
- Power BI Desktop re-serialises files on open (whitespace/formatting churn);
  these `M` changes are usually noise, safe to `git stash`/discard.

---

## 9. Layout & legibility — fixing truncation without breaking things

Hard-won from a 43-page / 570-visual legibility pass. The canvas is **1280 × 720**.
`validate_phm_repo.py` now guards layout (check 6): **off-canvas** and **two
substantial visuals overlapping >40%** (textbox/shape/image/button overlays are
excluded). Run it after any re-layout.

**Safe vs risky edit levers (from least to most risky):**
1. **`position` {x,y,width,height}** — 100% safe, no schema risk. This is the
   main lever: widen truncating bars/tables, grow short narratives, re-flow rows.
2. **`visualContainerObjects.title[].properties.text`** — safe; shorten over-long
   titles (keep the `'…'` quoting exact).
3. **Source-label shortening** (a SQL `CASE` in the model query) — safe and the
   best fix for long category labels, because it changes the **values**, not the
   column name, so **no visual.json edit is needed** (e.g. ICD cause-of-death
   chapters → "Circulatory"; bind stays on `cause_chapter`).
   - **Always sample the distinct source values before trusting a bar.** Three
     traps we keep hitting, all fixed at source (lever 3), all verified by a
     `select <col>, count(*) … group by 1` first:
     - **Raw codes masquerading as truncation** — `bnf_chapter` was 2-letter
       codes (`Ca`,`Ce`,`En`), not clipped words; expand with an explicit `CASE`.
     - **One entity, multiple encodings in the same column** — `diagnostic_tests`
       held both `NON_OBSTETRIC_ULTRASOUND` (UPPER_SNAKE, bulk) **and**
       `Non-obstetric ultrasound` (proper name) for the same DM01 test. Normalise
       with an **ILIKE-keyword `CASE`** (`when … ilike '%ultrasound%' then …`) so
       both forms collapse to one readable bar; the `group by` then merges them.
       Add an `else initcap(replace(lower(col),'_',' '))` net for unseen codes.
     - **Bare ordinal codes** — ACG `rub` was `0`–`5`; map to
       `'3 Moderate morbidity'` etc. **with a leading sort digit** so the axis
       still orders correctly (matches the `efi_band` `'1 Fit'` house style).
   - Values already carrying a leading sort prefix (`03 Low Need Adult`) or
     already readable (`incident_colour` = `Category 1`–`5`) are **not** code
     problems — leave them; their truncation is a width/title issue (lever 1).
4. **Model column display rename** (raw `snake_case` headers → friendly) — medium:
   ripples into measures *and* visual `queryRef`/`nativeQueryRef`. Keep
   `sourceColumn` unchanged; update every `Table[col]` DAX ref and every visual
   ref; **check model-wide name collisions first** (the validator catches them).
5. **`objects` formatting keys** (categoryAxis `wordWrap`/`fontSize`/rotate,
   column auto-size) — RISKY: the exact PBIR property format is version-specific
   and a wrong literal can fail the report import. **Avoid these** unless you can
   verify on the Service; prefer (1)+(3) instead.

**Truncation playbook (the #1 legibility problem — horizontal bars + tables):**
- Long category labels (specialty, crime type, BNF chapter, ONS cause, test):
  **widen** the bar if the row has room; if it's a **tight row** (e.g. 3 bars at
  x≈24/434/844, each ~400px), you can't widen — **shorten the labels at source**
  (lever 3), or shrink the least label-sensitive neighbour (a map/treemap) to
  hand width to the long-label bar.
- Tables with many columns crammed into <900px hide the right columns behind a
  scrollbar — widen toward the canvas edge (`x+width ≤ ~1264`) or drop columns.
- Narrative/insight cards need **≥ ~100px height** for multi-line text (cards
  ~78–100); too short → text cut with "…". Grow height and cascade the rows
  below down so nothing collides.

**Fan-out re-layout (multi-agent):** give each agent a **distinct set of pages**
(distinct files) → they never touch the same `visual.json`, so no worktree
isolation is needed and there's nothing to merge. Constrain agents to
**position + title-text only** (forbid any `query`/`queryRef`/`Property`/model
edit — that's how the `Report_Import_FailedToImportReport` happens), and make
them self-check JSON-parse + canvas-bounds + no-overlap before returning.

**Don't chase phantom mojibake.** Terminals and tool output render legit Unicode
(`—` em-dash, `·` middot, `£`) as `�`. The *files* are usually clean UTF-8 —
check the actual bytes for U+FFFD / `Â£` / `â€"` before "fixing" anything.

---

## 10. Themes, pages & the "half-worked deploy" diagnosis

Hard-won fixing a 37-page PDF where most legibility fixes *didn't appear* even
though the deploy "succeeded". `validate_phm_repo.py` now adds checks 8–10 for
the structural traps below.

**The registered custom theme caches by NAME — editing its JSON does NOT
re-apply it.** A `customTheme` of `type: RegisteredResources`
(`StaticResources/RegisteredResources/<name>.json`, referenced from
`report.json` `themeCollection.customTheme` + `resourcePackages`) is compiled
and applied **at import, keyed by name**. On "Update all", model/report-
definition changes deploy + refresh fine, but changed *theme content* keeps
rendering the **old cached theme** — telltale: new `dataColors`/font/
`showAxisTitle` never show. **Fix: bump the theme NAME** (e.g. `… → … v2`) in
**all three** places — the theme file's internal `name`, the `resourcePackages`
item `name` (+`path` if you rename the file), and `themeCollection.customTheme.
name` — to force a fresh registration. Check 8 verifies the three stay
consistent and the file exists (a partial rename silently drops you to the base
theme).

**Per-visual `objects` OVERRIDE the theme.** A chart that explicitly sets
`categoryAxis.showAxisTitle: true` still shows its axis title ("month_date",
"Year", `imd_decile`) even after the theme default goes false. Theme changes
only fix visuals that *inherit*; for the rest, set the property on the visual.
Conversely you can't assume a theme change reaches everything — spot-check.

**The "half-worked deploy" tell:** if model/data changes show (shortened labels,
merged categories, a chart-type swap) but colours/fonts/axis-titles **don't**,
it's the theme cache — not a failed sync. Don't re-edit the visuals; bump the
theme name.

**Long dynamic text measures need a TABLE, not a card.** Neither `card` nor
`multiRowCard` reliably **word-wraps** a long DAX text measure — they render one
line and clip (no `wordWrap`/height tweak fixes it). For insight/action/"The
Ask" prose, use a single-column, header-less **`tableEx`**:
`columnHeaders.show=false`, `values.wordWrap=true` + ~11pt, `grid` off,
`title.show=false`, keep the card background/border. The cell wraps and the row
grows; size the visual tall enough (tables **scroll**, they don't auto-grow the
container). Big-number KPIs stay `card`. **Watch the override trap:** these boxes
were cloned from a card carrying a per-visual `objects.dataLabels` block, and
**per-visual `objects` beat the theme** — so a theme-level wrap/font never
applied. When cloning, strip the per-visual overrides you don't want.

**Treemap with many categories is the wrong chart.** ~50 specialties in a
treemap = unreadable truncated tiles at any label length. Convert to a **sorted
horizontal `barChart`** (labels move to the y-axis): roles rename
`Group→Category`, `Values→Y`; add a `sortDefinition` (measure, Descending).
**Mirror an existing working `barChart`'s JSON exactly** rather than hand-build
it. No Top-N filter template existed in this repo — don't hand-roll a `TopN`
`filterConfig` blind (a bad one fails the whole report import); prefer
top-N-at-source bucketing if you must cap categories.

**Adding a page (PBIR):** a page is a folder under `definition/pages/<name>/`
with `page.json` + `visuals/<id>/visual.json` per visual. To add one: **clone an
existing page's chrome** (banner/title/rule/footer textboxes + a card +
multiRowCard) with **fresh ids where folder name == the visual.json `name`**
(check 10), bind cards/multiRowCards to existing measures (the field-ref check
confirms they resolve), and **register the page in `pages.json` `pageOrder`**
(check 9) — a folder not in `pageOrder` never displays.

**Board/exec content lives in report pages, not side documents.** "Make a 2-page
exec summary" means *two report pages* (e.g. `executive` = strategic case,
`executiveask` = the ask) bound to live measures — not a Word/PDF export. Build
it in the PBIP.

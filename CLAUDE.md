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

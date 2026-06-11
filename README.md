# BI_Reporting (Live Branch Guide)

This repository contains the source-controlled definition of the **One Gloucestershire BI reporting estate** in Microsoft Fabric / Power BI format.

The repository has multiple branches, but this document is intentionally focused on the **`live` branch** (the production-aligned content).

---

## What this repository is

On `live`, this is not a traditional application codebase (no web app, API service, or package-based build system).
It is a collection of **Power BI artifacts stored as files**, mainly:

- **Report items** (`*.Report`)
- **Semantic model items** (`*.SemanticModel`)
- **Archived historical items** under `01 Archive`

At the top level on `live` there are:

- **47 active report folders** (`*.Report`)
- **47 active semantic model folders** (`*.SemanticModel`)
- **14 archived report/model pairs** inside `01 Archive`

Each active report has a matching semantic model with the same base name.

---

## Repository structure on `live`

### 1) Report folders (`<Name>.Report`)

Each report folder contains the report definition and report-level resources.

Typical contents:

- `.platform`
  Fabric Git integration metadata (item type, display name, logical ID).
- `definition.pbir`
  Report definition metadata, including the dataset/semantic model path reference.
- `report.json`
  Main report payload (layout/configuration/theme/bookmarks and visual metadata).
- `StaticResources/RegisteredResources/*`
  Theme files, logos/images, and geospatial/shape resources used by visuals.
- `CustomVisuals/*` (in some reports)
  Packaged custom visual assets.

### 2) Semantic model folders (`<Name>.SemanticModel`)

Each semantic model folder contains data model metadata, query logic, and relationships.

Typical contents:

- `.platform`
  Fabric item metadata for the semantic model.
- `definition.pbism`
  Semantic model definition properties.
- `.pbi/editorSettings.json`
  Model editor behavior settings.
- `definition/`
  TMDL-based model breakdown:
  - `database.tmdl`
  - `model.tmdl`
  - `relationships.tmdl`
  - `expressions.tmdl`
  - `tables/*.tmdl`
  - `cultures/*.tmdl`

### 3) Archive folder (`01 Archive`)

`01 Archive` stores older or retired report/model pairs in the same file-based shape as active content.

---

## Key technologies used (live branch)

The `live` branch is centered on **Microsoft Fabric / Power BI artifact serialization**:

1. **PBIR report definition format**
   - `definition.pbir` and `report.json` represent report metadata and visual/layout config.

2. **PBISM semantic model metadata**
   - `definition.pbism` tracks semantic model properties.

3. **TMDL (Tabular Model Definition Language)**
   - Semantic model internals are stored as `.tmdl` files in `definition/`.
   - This includes model structure, tables, relationships, expressions, and cultures.

4. **Power Query M and SQL-based sourcing**
   - Query expressions in semantic models include Power Query logic and SQL source queries.
   - Example model expressions indicate SQL Server sources and transformation steps.

5. **Static design/resource assets**
   - JSON themes, logos, and map/shape resources are versioned alongside report definitions.

---

## How code/content is organized

### Pairing model

The central organizational pattern on `live` is **report + model pairing**:

- `X.Report` = presentation layer (pages, visuals, formatting, interactions)
- `X.SemanticModel` = data/model layer (tables, relationships, calculations, query logic)

`X.Report/definition.pbir` points to `../X.SemanticModel`, making the relationship explicit in source control.

### Granularity model

The semantic model is decomposed for reviewability:

- table definitions split into separate files (`definition/tables/*.tmdl`)
- relationships centralized (`relationships.tmdl`)
- expressions/query definitions centralized (`expressions.tmdl`)
- culture/localization in `cultures/*.tmdl`

This enables cleaner diffs and targeted code review compared with monolithic binary artifacts.

### Naming model

Folder names represent subject-area products (for example: Planned Care, Frailty, Urgent Care, Mental Health, Prescribing, etc.), with archived/reworked variants under `01 Archive`.

---

## What you will *not* find here on `live`

Because this repository is artifact-first rather than application-first, there are currently:

- no `package.json`/`pyproject.toml`-style dependency manifests
- no conventional app build pipeline in repo files
- no unit test framework in repo files
- no `.github/workflows` pipeline definitions in this branch snapshot

Validation is therefore typically performed through Fabric/Power BI authoring and deployment workflows, plus metadata review in Git.

---

## Practical navigation tips for contributors

1. Start from a target subject folder pair:
   - `<Subject>.Report`
   - `<Subject>.SemanticModel`
2. Check `.platform` first to confirm item identity and type.
3. Use `definition.pbir` to verify report-to-model linkage.
4. Review semantic model diffs in:
   - `definition/expressions.tmdl`
   - `definition/relationships.tmdl`
   - `definition/tables/*.tmdl`
5. Review report behavior/configuration in `report.json` and `StaticResources`.

---

## Branch focus note

This README intentionally documents the **live branch content and organization** only.
Other branches may exist for development/testing workflows, but details are excluded here by design.

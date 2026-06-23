#!/usr/bin/env python3
"""Pre-commit guard for the Gloucestershire Population Health PBIP.

Catches the import-killers we've hit repeatedly:
  1. UTF-8 BOM in any .tmdl/.json/.pbir file  (auto-stripped with --fix)
  2. Duplicate measure names across the model  (blocks import)
  3. A measure whose name matches ANY column anywhere in the model
     (case-insensitive, model-wide) — Power BI Desktop rejects this on open
     even though the Fabric Service import tolerates it.
  4. customTheme in report.json missing reportVersionAtImport
  5. visual field refs that don't resolve to a model column/measure
  6. layout: visuals pushed off the 1280x720 canvas, or two substantial
     visuals overlapping >40% (guards against re-layout/legibility mistakes;
     textbox/shape/image/button overlays are excluded)
  7. malformed Value.NativeQuery M (dangling T-SQL / odd-quote escaping)
  8. custom-theme resource integrity (report.json ref <-> manifest <-> file)
  9. pages.json pageOrder <-> page-folder consistency (unregistered/dangling)
 10. every visual.json 'name' equals its folder name (clone/rename mistakes)
 11. no duplicate item logicalId across .platform files (copy-without-dedup)
 12. no malformed TMDL (child property at column 0; inline-brace relationships)
  7. malformed Value.NativeQuery M in ANY report's SemanticModel (repo-wide) —
     dangling T-SQL fragment / broken "" escaping from a bad Sql.Database ->
     Redshift conversion; Fabric import dies "M Engine error: Token ',' expected"

Usage:  python validate_phm_repo.py [--fix]   (run from the BI_Reporting repo root)
Exit code 0 = clean, 1 = problems remain.
"""
import sys, os, re, json, glob, collections

FIX = "--fix" in sys.argv
ROOT = "Gloucestershire Population Health"
MODEL = f"{ROOT}.SemanticModel/definition"
REPORT = f"{ROOT}.Report/definition"
RPT_ROOT = f"{ROOT}.Report"
problems = []


def find(base, exts):
    out = []
    for f in glob.glob(os.path.join(base, "**", "*"), recursive=True):
        if os.path.isfile(f) and f.endswith(exts):
            out.append(f)
    return out


# 1) BOM check (+ optional auto-fix)
bom = []
for f in find(MODEL, (".tmdl", ".json")) + find(REPORT, (".tmdl", ".json", ".pbir", ".platform")):
    raw = open(f, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        if FIX:
            open(f, "wb").write(raw[3:])
        else:
            bom.append(os.path.relpath(f))
if bom:
    problems.append(f"UTF-8 BOM in {len(bom)} file(s): {bom[:5]} (run with --fix)")

# parse model tables -> columns + measures
def cols_meas(s):
    cols = {(a or b) for a, b in re.findall(r"^\tcolumn (?:'([^']+)'|(\S+))", s, re.M)}
    meas = {(a or b) for a, b in re.findall(r"^\tmeasure (?:'([^']+)'|(\S+))", s, re.M)}
    return cols, meas

model, seen = {}, collections.defaultdict(list)
all_cols = {}                       # lower(colname) -> (colname, table)  model-wide
for f in glob.glob(os.path.join(MODEL, "tables", "*.tmdl")):
    t = os.path.splitext(os.path.basename(f))[0]
    c, m = cols_meas(open(f, encoding="utf-8").read())
    model[t] = c | m
    for cn in c:
        all_cols.setdefault(cn.lower(), (cn, t))
    for mm in m:
        seen[mm].append(t)

# 2) duplicate measures
dups = {n: ts for n, ts in seen.items() if len(ts) > 1}
if dups:
    problems.append(f"Duplicate measure names (model-wide): {dups}")
# 3) measure name == column name ANYWHERE in the model (case-insensitive).
#    Power BI Desktop's AS engine refuses to create such a measure
#    (PFE_XL_MEASURE_COLUMN_ALREADY_EXIST) even when the column is in a
#    different table; the Service import does not, so this stays latent.
clash = []
for mm, ts in seen.items():
    if mm.lower() in all_cols:
        cn, ct = all_cols[mm.lower()]
        clash.append(f"measure '{mm}' ({ts[0]}) <-> column '{cn}' ({ct})")
if clash:
    problems.append("Measure/column name clashes (model-wide, Desktop-blocking): "
                    + "; ".join(sorted(clash)))

# 4) customTheme reportVersionAtImport
rj = os.path.join(REPORT, "report.json")
if os.path.isfile(rj):
    j = json.load(open(rj, encoding="utf-8"))
    ct = j.get("themeCollection", {}).get("customTheme")
    if ct and "reportVersionAtImport" not in ct:
        problems.append("report.json customTheme is missing 'reportVersionAtImport'")

# 5) unresolved visual field refs
unresolved = set()
for vf in glob.glob(os.path.join(REPORT, "pages", "*", "visuals", "*", "visual.json")):
    try:
        j = json.load(open(vf, encoding="utf-8"))
    except Exception as e:
        problems.append(f"Unparseable visual: {os.path.relpath(vf)} ({e})")
        continue

    def walk(o):
        if isinstance(o, dict):
            if "Expression" in o and "Property" in o:
                e = o["Expression"].get("SourceRef", {}).get("Entity")
                p = o["Property"]
                if e in model and p not in model[e]:
                    unresolved.add((e, p))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(j)
if unresolved:
    problems.append(f"Unresolved visual field refs: {sorted(unresolved)[:10]}")

# 6) layout sanity — catch re-layout mistakes: visuals pushed off the 1280x720
#    canvas, or two substantial visuals overlapping (textbox/shape/image/button
#    are excluded — they're legitimately layered, e.g. map-scale captions).
CANVAS_W, CANVAS_H = 1280, 720
OVERLAY = {"textbox", "shape", "image", "actionButton", "basicShape"}
oob, overlaps = [], []
for vdir in glob.glob(os.path.join(REPORT, "pages", "*", "visuals")):
    page = os.path.basename(os.path.dirname(vdir))
    subs = []
    for vf in glob.glob(os.path.join(vdir, "*", "visual.json")):
        try:
            j = json.load(open(vf, encoding="utf-8"))
        except Exception:
            continue
        vid = os.path.basename(os.path.dirname(vf))[:8]
        t = j.get("visual", {}).get("visualType", "")
        p = j.get("position", {})
        x, y, w, h = p.get("x", 0), p.get("y", 0), p.get("width", 0), p.get("height", 0)
        if x < -1 or y < -1 or x + w > CANVAS_W + 1 or y + h > CANVAS_H + 1:
            oob.append(f"{page}/{vid} ({int(x)},{int(y)},{int(w)},{int(h)})")
        if t not in OVERLAY:
            subs.append((vid, t, (x, y, w, h)))
    for i in range(len(subs)):
        for k in range(i + 1, len(subs)):
            (ai, at, a), (bi, bt, b) = subs[i], subs[k]
            ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
            sm = min(a[2] * a[3], b[2] * b[3]) or 1
            if ix * iy / sm > 0.4:
                overlaps.append(f"{page}: {ai}({at})<>{bi}({bt}) {ix*iy/sm:.0%}")
if oob:
    problems.append(f"Visuals off-canvas (>{CANVAS_W}x{CANVAS_H}): {oob[:8]}")
if overlaps:
    problems.append(f"Substantial visuals overlapping >40%: {overlaps[:8]}")

# 7) malformed Value.NativeQuery (REPO-WIDE) — guards the bulk Sql.Database ->
#    Redshift source migration. A non-greedy rewrite regex that stops at the
#    first `])` inside the original T-SQL (e.g. MAX([Year_Month])) leaves a
#    dangling fragment after the call, so Fabric import dies with
#    "M Engine error: Token ',' expected." A well-formed NativeQuery's closing
#    `[EnableFolding=true])` is ALWAYS immediately followed by ',' (next M step)
#    or a newline (then `in`/next step). Also flags odd `"` counts in the SQL
#    string (broken `""` escaping) and any partition still mixing Sql.Database
#    with NativeQuery. Scans every report's SemanticModel, not just PHM.
nq_bad = []
NQ_END = re.compile(r'\[EnableFolding=true\]\)')
NQ_STR = re.compile(r'Value\.NativeQuery\(AmazonRedshift\.Database\([^)]*\),\s*"(.*?)",\s*null,\s*\[EnableFolding=true\]\)', re.S)
for f in glob.glob("**/*.SemanticModel/definition/tables/*.tmdl", recursive=True):
    t = open(f, encoding="utf-8").read()
    if "Value.NativeQuery" not in t:
        continue
    why = None
    for m in NQ_END.finditer(t):
        nxt = t[m.end():m.end() + 1]
        if nxt not in (",", "\n", ""):
            why = f"dangling fragment after call ({nxt!r})"
            break
    for sm in NQ_STR.finditer(t):
        if sm.group(1).count('"') % 2:
            why = why or "odd quote count in SQL string (broken \"\" escaping)"
    if why:
        nq_bad.append(f"{os.path.relpath(f)} [{why}]")
if nq_bad:
    problems.append(f"Malformed Value.NativeQuery M in {len(nq_bad)} file(s): {nq_bad[:8]}")

# 8) custom-theme resource integrity — the registered theme referenced by
#    report.json must have a matching resourcePackages item whose file exists.
#    A rename that updates only some of {file name, manifest path/name,
#    customTheme.name} silently drops the custom theme back to the base theme.
#    NB: a registered theme caches by NAME — to actually re-deploy changed theme
#    JSON you must BUMP THE NAME in all three places (see CLAUDE.md §6).
rjp = os.path.join(REPORT, "report.json")
if os.path.isfile(rjp):
    rj = json.load(open(rjp, encoding="utf-8"))
    ct = (rj.get("themeCollection", {}) or {}).get("customTheme", {}) or {}
    name = ct.get("name")
    if name:
        items = [it for pkg in rj.get("resourcePackages", [])
                 if pkg.get("type") == "RegisteredResources"
                 for it in pkg.get("items", []) if it.get("type") == "CustomTheme"]
        match = [it for it in items if it.get("name") == name]
        if not match:
            problems.append(f"customTheme '{name}' has no matching RegisteredResources "
                            f"CustomTheme item (theme falls back to base)")
        else:
            tp = os.path.join(RPT_ROOT, "StaticResources", "RegisteredResources",
                              match[0].get("path", ""))
            if not os.path.isfile(tp):
                problems.append(f"customTheme '{name}' file missing on disk: "
                                f"{match[0].get('path')}")

# 9) pages.json <-> page-folder consistency. A page folder not in pageOrder never
#    displays; a pageOrder entry with no folder is a dangling reference.
pagesdir = os.path.join(REPORT, "pages")
pjp = os.path.join(pagesdir, "pages.json")
if os.path.isfile(pjp):
    order = json.load(open(pjp, encoding="utf-8")).get("pageOrder", [])
    folders = {d for d in os.listdir(pagesdir)
               if os.path.isfile(os.path.join(pagesdir, d, "page.json"))}
    not_listed = sorted(folders - set(order))
    no_folder = sorted(set(order) - folders)
    if not_listed:
        problems.append(f"page folders missing from pages.json pageOrder "
                        f"(won't display): {not_listed}")
    if no_folder:
        problems.append(f"pages.json pageOrder entries with no folder: {no_folder}")

# 10) every visual.json 'name' must equal its folder name (clone/rename mistake).
namemismatch = []
for vf in glob.glob(os.path.join(REPORT, "pages", "*", "visuals", "*", "visual.json")):
    folder = os.path.basename(os.path.dirname(vf))
    try:
        nm = json.load(open(vf, encoding="utf-8")).get("name")
    except Exception:
        continue
    if nm != folder:
        namemismatch.append(f"{folder} (name='{nm}')")
if namemismatch:
    problems.append(f"visual.json 'name' != folder: {namemismatch[:8]}")

# 11) duplicate item logical IDs across ALL .platform files (repo-wide). Copying
#     a report/model folder without regenerating its `config.logicalId` (and
#     renaming `metadata.displayName`) makes Fabric raise "Fix duplicate logical
#     IDs" and jams git sync for the originals. (Caused by PR #76's '1.ICS Report'
#     copy.) Scans every item in the repo, not just PHM.
lid_map = collections.defaultdict(list)
for pf in glob.glob("**/.platform", recursive=True):
    try:
        pj = json.load(open(pf, encoding="utf-8"))
    except Exception:
        continue
    lid = pj.get("config", {}).get("logicalId")
    if lid:
        lid_map[lid].append(os.path.dirname(pf) or ".")
dup_lids = {k: v for k, v in lid_map.items() if len(v) > 1}
if dup_lids:
    problems.append("Duplicate item logicalId(s) across items (Fabric will jam "
                    "sync): " + "; ".join(f"{k} -> {v}" for k, v in dup_lids.items()))

# 12) Malformed TMDL relationships (repo-wide). These fail Fabric import with
#     Workload_FailedToParseFile / "Invalid indentation". TMDL is indentation-
#     based: `fromColumn`/`toColumn` are ALWAYS nested under a `relationship`
#     block so they MUST be indented, and there is no inline-brace
#     `relationship X Y { ... }` form. (Grok's 1.ICS Report relationships.tmdl
#     had both — column-0 fromColumn/toColumn and brace syntax — which jammed
#     the whole workspace's git sync.)
tmdl_bad = []
for f in glob.glob("**/*.tmdl", recursive=True):
    try:
        lines = open(f, encoding="utf-8").read().splitlines()
    except Exception:
        continue
    for i, ln in enumerate(lines, 1):
        # child-only TMDL properties are ALWAYS indented under a table/column/
        # measure/relationship — at column 0 they are an "Invalid indentation"
        # import error (Grok's whole 1.ICS table batch was written this way).
        if re.match(r"^(lineageTag|fromColumn|toColumn|sourceColumn|summarizeBy|"
                    r"dataType|formatString|sortByColumn|displayFolder|isHidden|"
                    r"isKey|isNameInferred|isDataTypeInferred)\b", ln):
            tmdl_bad.append(f"{os.path.relpath(f)}:{i} unindented "
                            f"'{ln.strip()[:36]}' (TMDL child property at column 0)")
        elif re.match(r"^\s*relationship\b.*\{", ln):
            tmdl_bad.append(f"{os.path.relpath(f)}:{i} inline-brace relationship "
                            f"syntax (TMDL is indentation-based)")
if tmdl_bad:
    problems.append(f"Malformed TMDL relationships ({len(tmdl_bad)}): {tmdl_bad[:6]}")

if problems:
    print("PHM VALIDATION FAILED:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print(f"PHM validation OK — {len(model)} tables, {sum(len(v) for v in seen.values())} measures, BOM-clean, refs resolve.")

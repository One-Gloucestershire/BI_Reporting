#!/usr/bin/env python3
"""Pre-commit guard for the Gloucestershire Population Health PBIP.

Catches the import-killers we've hit repeatedly:
  1. UTF-8 BOM in any .tmdl/.json/.pbir file  (auto-stripped with --fix)
  2. Duplicate measure names across the model  (blocks import)
  3. A measure whose name matches a column in the same table (case-insensitive)
  4. customTheme in report.json missing reportVersionAtImport
  5. visual field refs that don't resolve to a model column/measure

Usage:  python validate_phm_repo.py [--fix]   (run from the BI_Reporting repo root)
Exit code 0 = clean, 1 = problems remain.
"""
import sys, os, re, json, glob, collections

FIX = "--fix" in sys.argv
ROOT = "Gloucestershire Population Health"
MODEL = f"{ROOT}.SemanticModel/definition"
REPORT = f"{ROOT}.Report/definition"
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

model, seen, clash = {}, collections.defaultdict(list), []
for f in glob.glob(os.path.join(MODEL, "tables", "*.tmdl")):
    t = os.path.splitext(os.path.basename(f))[0]
    c, m = cols_meas(open(f, encoding="utf-8").read())
    model[t] = c | m
    low = {x.lower() for x in c}
    for mm in m:
        seen[mm].append(t)
        if mm.lower() in low:
            clash.append((t, mm))

# 2) duplicate measures
dups = {n: ts for n, ts in seen.items() if len(ts) > 1}
if dups:
    problems.append(f"Duplicate measure names (model-wide): {dups}")
# 3) measure==column clash
if clash:
    problems.append(f"Measure/column name clashes: {clash}")

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

if problems:
    print("PHM VALIDATION FAILED:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print(f"PHM validation OK — {len(model)} tables, {sum(len(v) for v in seen.values())} measures, BOM-clean, refs resolve.")

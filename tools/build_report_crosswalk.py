#!/usr/bin/env python3
"""
Report-consumer crosswalk for the BI_Reporting cloud (Redshift) migration.

Builds the layer the warehouse crosswalk (data_warehouse/catalog) is missing:
links every Power BI report PARTITION to the data source it reads and its
migration status, then joins to the warehouse crosswalk's mart parity so you
get end-to-end lineage:

    on-prem table  ->  RS mart (parity band)  ->  report partition  ->  converted?

Read-only over the repo. Emits report_crosswalk.json + REPORT_CROSSWALK.md.
No cluster access needed (status is derived from the TMDL M source).
"""
import re, glob, json, pathlib
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
XWALK = pathlib.Path("C:/data_warehouse/catalog/site/crosswalk.json")

NQ    = re.compile(r'Value\.NativeQuery\(AmazonRedshift\.Database\("[^"]+","([^"]+)"\)\s*,\s*"((?:[^"]|"")*)"', re.S)
SQLDB = re.compile(r'Sql\.Database\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*\[Query="((?:[^"]|"")*)"', re.S)
FILE  = re.compile(r'(File\.Contents|Excel\.Workbook|Csv\.Document|SharePoint\.\w+|Folder\.Files|Web\.Contents)')

RS_DBS = ("db02_nopid", "db01_reference", "db03_pid", "db03_pid_reporting")
def from_tables(sql):
    sql = sql.replace('""', '"')
    out = set()
    for m in re.findall(r'\b(?:from|join)\s+([\w\.\[\]"]+)', sql, re.I):
        t = re.sub(r'[\[\]"]', '', m).lower()
        if "." not in t: continue                     # drop subquery aliases (t, v, _v, a, b...)
        parts = t.split(".")
        if parts[0] in RS_DBS: parts = parts[1:]       # normalise RS db-qualified -> schema.table
        out.add(".".join(parts))
    return sorted(out)

def classify(block):
    """Return (status, db, targets) for one partition/expression source block."""
    m = NQ.search(block)
    if m: return ("redshift", m.group(1), from_tables(m.group(2)))
    m = SQLDB.search(block)
    if m: return ("onprem", m.group(2), from_tables(m.group(3)))
    if FILE.search(block): return ("file", None, [])
    return ("calculated", None, [])   # DAX CALENDAR / GENERATESERIES / constant tables

def partitions_of(path):
    """Yield (partition_name, source_block) for a .tmdl file."""
    txt = path.read_text(encoding="utf-8")
    if path.name == "expressions.tmdl":
        for m in re.finditer(r'expression\s+(\'[^\']+\'|"[^"]+"|[\w\.]+)\s*=(.*?)(?=\nexpression\s|\Z)', txt, re.S):
            yield (m.group(1).strip("'\""), m.group(2))
    else:
        # one (or rarely more) partition per table file
        parts = re.findall(r'partition\s+(\'[^\']+\'|"[^"]+"|[\w\.]+)\s*=\s*m\b(.*?)(?=\npartition\s|\Z)', txt, re.S)
        if parts:
            for name, body in parts: yield (name.strip("'\""), body)
        else:
            yield (path.stem, txt)   # calculated table, no m-partition

# ---- warehouse crosswalk parity lookup (RS object name -> band/status) ----
parity = {}
if XWALK.exists():
    xw = json.load(open(XWALK))
    for r in xw.get("rows", []):
        rs = (r.get("redshift") or "").strip().lower()
        if rs: parity[rs] = {"band": r.get("band", ""), "status": r.get("status", ""), "rs_rows": r.get("redshift_rows", "")}

def mart_parity(targets):
    for t in targets:
        key = t.split(".")[-1] if "." in t else t
        for k, v in parity.items():
            if k.endswith(key) or key in k:
                return v
    return None

# ---- walk reports ----
reports = {}
mart_consumers = defaultdict(list)   # rs target -> [(report, partition)]
onprem_sources = defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "*.SemanticModel"))):
    rep = pathlib.Path(d).name[:-14]
    if rep.startswith("01 Archive"): continue
    rows = []
    for tf in glob.glob(d + "/definition/tables/*.tmdl") + glob.glob(d + "/definition/expressions.tmdl"):
        for pname, block in partitions_of(pathlib.Path(tf)):
            status, db, targets = classify(block)
            row = {"partition": pname, "status": status, "db": db, "targets": targets}
            if status == "redshift":
                par = mart_parity(targets)
                if par: row["parity"] = par
                for t in targets: mart_consumers[t].append((rep, pname))
            elif status == "onprem":
                for t in targets: onprem_sources[t].append((rep, pname))
            rows.append(row)
    cnt = Counter(r["status"] for r in rows)
    sqlish = cnt["redshift"] + cnt["onprem"]
    reports[rep] = {
        "partitions": rows, "counts": dict(cnt),
        "pct_converted": round(100 * cnt["redshift"] / sqlish) if sqlish else None,
        "fully_on_redshift": cnt["onprem"] == 0 and cnt["redshift"] > 0,
    }

# ---- gaps ----
gaps_md = (ROOT / "refdata-gaps.md")
gaps_text = gaps_md.read_text(encoding="utf-8") if gaps_md.exists() else ""

# ---- totals ----
tot = Counter()
for r in reports.values():
    for k, v in r["counts"].items(): tot[k] += v
sqlish = tot["redshift"] + tot["onprem"]
summary = {
    "reports": len(reports),
    "reports_fully_on_redshift": sum(1 for r in reports.values() if r["fully_on_redshift"]),
    "partition_status": dict(tot),
    "pct_sql_converted": round(100 * tot["redshift"] / sqlish, 1) if sqlish else None,
    "distinct_rs_marts_consumed": len(mart_consumers),
    "distinct_onprem_sources_remaining": len(onprem_sources),
}
out = {"summary": summary, "reports": reports,
       "mart_consumers": {k: v for k, v in sorted(mart_consumers.items())},
       "remaining_onprem_sources": {k: v for k, v in sorted(onprem_sources.items())}}
json.dump(out, open(ROOT / "report_crosswalk.json", "w"), indent=1)

# ---- markdown ----
L = []
L.append("# BI_Reporting → Redshift — report-consumer crosswalk\n")
L.append("End-to-end lineage for the cloud migration: every report partition, the source it reads, "
         "its migration status, and (for converted ones) the warehouse crosswalk parity of the mart it hits. "
         "Generated by `tools/build_report_crosswalk.py` (read-only over the TMDL).\n")
s = summary
L.append(f"**{s['pct_sql_converted']}% of SQL partitions on Redshift** "
         f"({tot['redshift']} converted / {tot['onprem']} still on-prem) · "
         f"**{s['reports_fully_on_redshift']}/{s['reports']} reports fully on Redshift** · "
         f"file/gateway sources: {tot['file']} · calculated: {tot['calculated']}\n")
L.append("## Per-report status\n")
L.append("| Report | RS | on-prem | file | calc | % SQL | done |")
L.append("|---|--:|--:|--:|--:|--:|:--:|")
for rep in sorted(reports, key=lambda r: (reports[r]["counts"].get("onprem", 0) == 0, -reports[r]["counts"].get("onprem", 0))):
    c = reports[rep]["counts"]; r = reports[rep]
    done = "✅" if r["fully_on_redshift"] else ("—" if c.get("onprem", 0) else "")
    L.append(f"| {rep} | {c.get('redshift',0)} | {c.get('onprem',0)} | {c.get('file',0)} | {c.get('calculated',0)} "
             f"| {r['pct_converted'] if r['pct_converted'] is not None else '-'}% | {done} |")
L.append("\n## Remaining on-prem sources (the blockers, by source table)\n")
L.append("| on-prem source | # partitions | consuming reports |")
L.append("|---|--:|---|")
for src, cons in sorted(out["remaining_onprem_sources"].items(), key=lambda x: -len(x[1])):
    reps_list = ", ".join(sorted({c[0] for c in cons}))
    L.append(f"| `{src}` | {len(cons)} | {reps_list[:80]} |")
L.append("\n## Top consumed RS marts (reverse index)\n")
L.append("| RS mart | # report partitions | parity |")
L.append("|---|--:|:--:|")
for mart, cons in sorted(out["mart_consumers"].items(), key=lambda x: -len(x[1]))[:30]:
    par = mart_parity([mart]); band = par["band"] if par else ""
    L.append(f"| `{mart}` | {len(cons)} | {band} |")
if gaps_text:
    L.append("\n## Session-reported gaps (refdata-gaps.md)\n")
    L.append("```\n" + gaps_text.strip()[:3000] + "\n```")
(ROOT / "REPORT_CROSSWALK.md").write_text("\n".join(L), encoding="utf-8")
print("wrote report_crosswalk.json + REPORT_CROSSWALK.md")
print(json.dumps(summary, indent=1))

#!/usr/bin/env python3
"""Idempotent visual-polish pass for the Gloucestershire Population Health PBIP.

Batch C (this pass): hide the redundant slicer *header* (which renders the raw
field name e.g. "lad", "pcn", "imd_decile") on every slicer that already has a
friendly *title*. The title stays; the dropdown control stays; only the raw
field-name sub-label is removed.

Run from the BI_Reporting repo root:  python tools/polish_phm_visuals.py
Re-running is safe (idempotent).
"""
import json, glob, os, sys

REPORT = "Gloucestershire Population Health.Report/definition"
VISUALS = sorted(glob.glob(os.path.join(REPORT, "pages", "*", "visuals", "*", "visual.json")))

FALSE_EXPR = {"expr": {"Literal": {"Value": "false"}}}


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def has_title_text(visual):
    """True if the slicer has an explicit title text set (friendly label)."""
    for loc in (visual.get("objects", {}), visual.get("visualContainerObjects", {})):
        for t in loc.get("title", []) or []:
            props = t.get("properties", {})
            if "text" in props:
                return True
    return False


changed, skipped_no_title = [], []
for vf in VISUALS:
    j = load(vf)
    vis = j.get("visual", {})
    if vis.get("visualType") != "slicer":
        continue
    if not has_title_text(vis):
        skipped_no_title.append(vf)
        continue
    objects = vis.setdefault("objects", {})
    header = objects.setdefault("header", [{}])
    props = header[0].setdefault("properties", {})
    if props.get("show") == FALSE_EXPR:
        continue  # already hidden -> idempotent
    props["show"] = FALSE_EXPR
    dump(vf, j)
    changed.append(vf)

print(f"slicer headers hidden: {len(changed)}")
for c in changed:
    print("  +", os.path.relpath(c, REPORT))
if skipped_no_title:
    print(f"\nslicers WITHOUT a title (left for manual review): {len(skipped_no_title)}")
    for s in skipped_no_title:
        print("  ?", os.path.relpath(s, REPORT))

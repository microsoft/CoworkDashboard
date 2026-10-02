#!/usr/bin/env python3
"""
build_dashboard.py — render team_data.json (from parse_posts.py) into a single
self-contained, team-safe HTML dashboard.

v1 scope: small, homogeneous teams at the team level. Anonymized — members are
numbers, the only attribute is Role, and NOTHING is shown at an individual level.
A per-Role breakdown appears only when >= kThreshold members share that Role
(privacy k-anonymity); otherwise contributors collapse into one combined bar.

Tabs (each small, one clear purpose):
  Overview          — auto-insights + the single KPI band.
  Impact & Value    — task categories ($), roles (+ skills as collapsible detail),
                      deliverables by FILE FORMAT.
  How Cowork is used— business process accordion: each row EXPANDS to its deliverable formats + skills
                      (skills nest in a sub-expand when long); category mix (k-anon), analyzed->produced.
  How to read       — definitions, the value model, privacy rule, and sources.

The "modeled tool-impact, not performance" disclaimer lives in the blue header; it is not a tab.

Every $ figure = hours x rate, computed live in the browser (live rate control).
Usage: python build_dashboard.py --in working/team_data.json --out output/cowork-team-roi-dashboard.html
"""
import json, argparse, re
from pathlib import Path

ASSET_DIR = Path(__file__).with_name("dashboard_assets")


def read_asset(name):
    path = ASSET_DIR / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"required dashboard asset is unavailable: {path}") from exc


CSS = read_asset("dashboard.css")
JS = read_asset("dashboard.js")
TEMPLATE = read_asset("dashboard.html")


def extract_glossary(template):
    m = re.search(r'id="gloss-body">(.*?)</div></details>', template, re.S)
    if not m:
        return {}
    g = {}
    for pm in re.finditer(r"<p><b>(.*?)</b>\s*\u2014\s*(.*?)</p>", m.group(1), re.S):
        term = re.sub(r"<[^>]+>", "", pm.group(1)).strip()
        definition = re.sub(r"</?i>", "", pm.group(2)).strip()
        if term:
            g[term.lower()] = definition
    return g


def main(a):
    data = json.load(open(a.inp, encoding="utf-8"))
    glossary = extract_glossary(TEMPLATE)
    html = (TEMPLATE.replace("__CSS__", CSS).replace("__JS__", JS)
            .replace("__GLOSSARY__", json.dumps(glossary, ensure_ascii=False))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__TEAM__", data["meta"].get("team", "Team"))
            .replace("__GENERATED__", str(data["meta"].get("generated", "")))
            .replace("__RATE__", str(data["meta"].get("defaultRate", 72)))
            .replace("__RECAP__", str(int(round(float(data["meta"].get("defaultRecapture", 0.70)) * 100))))
            .replace("__KTHRESH__", str(data["meta"].get("kThreshold", 3))))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_dashboard] wrote {a.out} ({len(html)} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--out", default="output/cowork-team-roi-dashboard.html")
    main(ap.parse_args())

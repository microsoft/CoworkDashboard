#!/usr/bin/env python3
"""
build_outputs.py — ONE build step for the team rollup: renders BOTH the self-contained HTML
dashboard AND the one-page landscape PDF interpretation guide from a single team_data.json, in a
single invocation, so the manager approves the build ONCE (not once per script).

It simply drives the two existing builders:
  - build_dashboard.py  → output/cowork-team-roi-dashboard.html   (stdlib only)
  - build_guide_pdf.py  → output/how-to-read-team-roi-dashboard.pdf (reportlab)
Both remain usable on their own; this wrapper only removes the second approval prompt.

The EMAIL send that follows (SendEmailWithAttachments to the channel members) is a SEPARATE,
expected approval — it is intentionally not bundled here.

Usage:
  python build_outputs.py --in working/team_data.json \
         [--config config/team_config.json] \
         [--out-html output/cowork-team-roi-dashboard.html] \
         [--out-pdf  output/how-to-read-team-roi-dashboard.pdf]
"""
import argparse, os, sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_dashboard          # noqa: E402
import build_guide_pdf          # noqa: E402


def main(a):
    for p in (a.out_html, a.out_pdf):
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
    # 1) HTML dashboard
    build_dashboard.main(SimpleNamespace(inp=a.inp, out=a.out_html))
    # 2) one-page PDF guide (reads the same team_data.json for team name + rate)
    build_guide_pdf.main(SimpleNamespace(out=a.out_pdf, data=a.inp, config=a.config))
    print(f"[build_outputs] built both outputs in one step → {a.out_html} + {a.out_pdf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--config", default="config/team_config.json")
    ap.add_argument("--out-html", dest="out_html", default="output/cowork-team-roi-dashboard.html")
    ap.add_argument("--out-pdf", dest="out_pdf", default="output/how-to-read-team-roi-dashboard.pdf")
    main(ap.parse_args())

#!/usr/bin/env python3
"""
build_outputs.py — ONE build step for the team rollup: renders the self-contained HTML dashboard
from a single team_data.json.

The interpretation guide is now FOLDED INTO the dashboard itself — the "How to read" tab plus a
clickable "?" helper on every section title — so the standalone one-page PDF is no longer built or
emailed by default. Recipients had been missing the separate attachment and toggling between two
files; keeping the guide inside the dashboard removes that friction.

The legacy one-page PDF guide (build_guide_pdf.py) is still available for anyone who wants a
printable copy: pass --with-pdf to regenerate it. It is NOT part of the default flow.

The EMAIL send that follows (SendEmailWithAttachments to the channel members) is a SEPARATE,
expected approval — it is intentionally not bundled here.

Usage:
  python build_outputs.py --in working/team_data.json \
         [--config config/team_config.json] \
         [--out-html output/cowork-team-roi-dashboard.html] \
         [--with-pdf [--out-pdf output/how-to-read-team-roi-dashboard.pdf]]
"""
import argparse, os, sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_dashboard          # noqa: E402


def main(a):
    d = os.path.dirname(a.out_html)
    if d:
        os.makedirs(d, exist_ok=True)
    # HTML dashboard — the interpretation guide is built into it (the "How to read" tab).
    build_dashboard.main(SimpleNamespace(inp=a.inp, out=a.out_html))
    if getattr(a, "with_pdf", False):
        import build_guide_pdf   # optional (reportlab) — only imported when explicitly requested
        dp = os.path.dirname(a.out_pdf)
        if dp:
            os.makedirs(dp, exist_ok=True)
        build_guide_pdf.main(SimpleNamespace(out=a.out_pdf, data=a.inp, config=a.config))
        print(f"[build_outputs] built dashboard + optional legacy PDF guide → {a.out_html} + {a.out_pdf}")
    else:
        print(f"[build_outputs] built dashboard (guide folded into its 'How to read' tab) → {a.out_html}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--config", default="config/team_config.json")
    ap.add_argument("--out-html", dest="out_html", default="output/cowork-team-roi-dashboard.html")
    ap.add_argument("--with-pdf", dest="with_pdf", action="store_true",
                    help="Also regenerate the legacy one-page PDF guide (off by default; the guide is now in-dashboard)")
    ap.add_argument("--out-pdf", dest="out_pdf", default="output/how-to-read-team-roi-dashboard.pdf")
    main(ap.parse_args())

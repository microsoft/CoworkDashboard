#!/usr/bin/env python3
"""
build_guide_pdf.py — render the one-page, LANDSCAPE "How to read your Team Cowork ROI dashboard"
interpretation guide that is emailed alongside the HTML dashboard.

A visual, plain-language legend: every KPI, the five tabs, the two controls, the privacy model,
and the methodology — on a single landscape page. Team name + hourly rate are pulled from
team_data.json when available (falls back to the config, then to sensible defaults), so the guide
always matches the dashboard it ships with.

Dependencies: reportlab (pre-installed in the Copilot Cowork container). Stdlib-only json/argparse
otherwise. The core pipeline (parse_posts.py / build_dashboard.py) stays stdlib-only; only this
optional guide generator uses reportlab.

Usage:
  python build_guide_pdf.py --out output/how-to-read-team-roi-dashboard.pdf \
         [--data working/team_data.json] [--config config/team_config.json]
"""
import argparse, json, os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

BLUE   = HexColor("#0f6cbd"); BLUEDK = HexColor("#0a4d86")
INK    = HexColor("#222222"); MUTE   = HexColor("#605E5C")
TILEBG = HexColor("#F3F7FB"); BORDER = HexColor("#D6E4F0")
GREEN  = HexColor("#107C41"); GOLD   = HexColor("#B88217"); PURPLE = HexColor("#5C2E91")
WHITE  = HexColor("#FFFFFF")


def load_meta(data_path, config_path):
    team, rate = "your team", 72
    for p in (data_path, config_path):
        if p and os.path.exists(p):
            try:
                j = json.load(open(p, encoding="utf-8"))
                meta = j.get("meta", j)
                team = meta.get("team") or j.get("team_name") or team
                rate = meta.get("defaultRate") or j.get("hourly_rate") or rate
            except Exception:
                pass
    return team, int(rate)


def build(out, team, rate):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    W, H = landscape(letter)          # 792 x 612
    c = canvas.Canvas(out, pagesize=landscape(letter))

    def para(x, y, text, font, size, color, maxw, lead):
        c.setFont(font, size); c.setFillColor(color)
        for ln in simpleSplit(text, font, size, maxw):
            c.drawString(x, y, ln); y -= lead
        return y

    def tile(x, y, w, h, accent, title, body, num=None):
        c.setFillColor(TILEBG); c.setStrokeColor(BORDER); c.setLineWidth(1)
        c.roundRect(x, y, w, h, 6, stroke=1, fill=1)
        c.setFillColor(accent); c.roundRect(x, y + h - 4, w, 4, 2, stroke=0, fill=1)
        tx, ty = x + 10, y + h - 16
        if num is not None:
            c.setFillColor(accent); c.circle(tx + 6, ty - 1, 8, stroke=0, fill=1)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(tx + 6, ty - 4, str(num)); tx += 20
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 9.5)
        c.drawString(tx, ty - 3, title)
        para(x + 10, ty - 16, body, "Helvetica", 8, MUTE, w - 20, 9.6)

    # header
    c.setFillColor(BLUE); c.rect(0, H - 64, W, 64, stroke=0, fill=1)
    c.setFillColor(BLUEDK); c.rect(0, H - 64, 6, 64, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 19)
    c.drawString(40, H - 34, "How to Read Your Team Cowork ROI Dashboard")
    c.setFont("Helvetica", 10.5)
    c.drawString(40, H - 52, "A one-page guide to every number, tab and control — anonymized and team-level only.")
    c.setFont("Helvetica-Bold", 9); c.drawRightString(W - 40, H - 40, str(team)[:34])
    c.setFont("Helvetica", 8); c.drawRightString(W - 40, H - 52, "Powered by Copilot Cowork")

    # 1 — KPI band
    y = H - 84
    c.setFillColor(BLUE); c.circle(48, y + 3, 8, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 10); c.drawCentredString(48, y, "1")
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 12)
    c.drawString(62, y - 2, "The KPI band  —  your headline numbers at a glance")
    kpis = [
        (BLUE,  "Time saved",            "Expert-equivalent hours Cowork saved the team this period."),
        (GREEN, "Value / cost reduction","Those saved hours priced out  (hours x hourly rate)."),
        (PURPLE,"Team speed multiplier", "How much faster:  expert hours / hands-on hours."),
        (GOLD,  "Contributors",          "How many teammates posted their stats this period."),
        (BLUE,  "Sessions",              "Distinct Cowork chats run across the whole team."),
        (GREEN, "Deliverables",          "Files, decks, docs, web pages and other outputs made."),
        (PURPLE,"Active days",           "Days with at least one Cowork task in the window."),
        (GOLD,  "Hands-on time",         "Real time at the keyboard (the assisted clock)."),
    ]
    cols, gap = 4, 12
    tw = (W - 80 - gap * (cols - 1)) / cols
    th, x0, row_top = 50, 40, y - 16
    for i, (acc, t, b) in enumerate(kpis):
        r, cc = divmod(i, cols)
        tile(x0 + cc * (tw + gap), row_top - r * (th + 8) - th, tw, th, acc, t, b)

    # 2 — tabs
    y2 = row_top - 2 * (th + 8) - 18
    c.setFillColor(BLUE); c.circle(48, y2 + 3, 8, stroke=0, fill=1)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 10); c.drawCentredString(48, y2, "2")
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 12)
    c.drawString(62, y2 - 2, "The five tabs  —  where to look for what")
    tabs = [
        ("Overview",           "Auto-insights + the KPI band. Start here."),
        ("Impact & Value",     "Value by pillar & task category ($), roles, deliverables."),
        ("How Cowork is used", "Top business processes, skills, analyzed -> produced."),
        ("Trends",             "Fortnight-over-fortnight movement over time."),
        ("Glossary & method",  "Plain-language definitions + the methodology."),
    ]
    tcols, tgap = 5, 10
    ttw = (W - 80 - tgap * (tcols - 1)) / tcols
    tth, ty2 = 46, y2 - 16
    for i, (t, b) in enumerate(tabs):
        x = 40 + i * (ttw + tgap); yb = ty2 - tth
        c.setFillColor(WHITE); c.setStrokeColor(BLUE); c.setLineWidth(1.2)
        c.roundRect(x, yb, ttw, tth, 6, stroke=1, fill=1)
        c.setFillColor(BLUE); c.roundRect(x, yb + tth - 15, ttw, 15, 6, stroke=0, fill=1)
        c.rect(x, yb + tth - 15, ttw, 8, stroke=0, fill=1)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8.6)
        c.drawCentredString(x + ttw / 2, yb + tth - 11, t)
        para(x + 8, yb + tth - 24, b, "Helvetica", 7.6, MUTE, ttw - 16, 9)

    # 3 & 4 — bottom panels
    yb2 = ty2 - tth - 20
    panel_h = yb2 - 44
    half = (W - 80 - 14) / 2
    lx = 40
    c.setFillColor(HexColor("#EAF3FB")); c.setStrokeColor(BORDER); c.setLineWidth(1)
    c.roundRect(lx, 44, half, panel_h, 7, stroke=1, fill=1)
    c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 10.5)
    c.drawString(lx + 12, 44 + panel_h - 18, "3   Controls you can change")
    yy = para(lx + 14, 44 + panel_h - 36,
              "Period selector  —  pick the reporting window; every number on the page updates to match.",
              "Helvetica", 8.6, INK, half - 28, 11) - 3
    para(lx + 14, yy,
         "Hourly-rate box  —  change $/hr and all value / cost-reduction figures recompute instantly "
         "(default $%d/hr)." % rate, "Helvetica", 8.6, INK, half - 28, 11)
    rx = 40 + half + 14
    c.setFillColor(HexColor("#F1F7F1")); c.setStrokeColor(HexColor("#CDE6D3")); c.setLineWidth(1)
    c.roundRect(rx, 44, half, panel_h, 7, stroke=1, fill=1)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 10.5)
    c.drawString(rx + 12, 44 + panel_h - 18, "4   Privacy & anonymity")
    yy = para(rx + 14, 44 + panel_h - 36,
              "Fully aggregated — no names, file names or prompts ever appear; numbers only.",
              "Helvetica", 8.6, INK, half - 28, 11) - 3
    para(rx + 14, yy,
         "A Role is shown only when at least 3 people share it (k-anonymity). Small teams show one "
         "combined view — that is expected.", "Helvetica", 8.6, INK, half - 28, 11)

    # footer methodology strip
    c.setFillColor(HexColor("#FBF6EA")); c.setStrokeColor(HexColor("#EAD9AE")); c.setLineWidth(1)
    c.roundRect(40, 20, W - 80, 20, 4, stroke=1, fill=1)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
    c.drawString(50, 27, "How the math works:")
    c.setFillColor(MUTE); c.setFont("Helvetica", 8)
    c.drawString(140, 27, "Time saved = research-anchored per-category time bands x run tasks   -   "
                          "Value = expert hours x hourly rate   -   Speed multiplier is directional "
                          "(expert / modeled hands-on clock).")
    c.showPage(); c.save()


def main(a):
    team, rate = load_meta(a.data, a.config)
    build(a.out, team, rate)
    print(f"[build_guide_pdf] wrote {a.out}  (team={team!r}, rate=${rate}/hr)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/how-to-read-team-roi-dashboard.pdf")
    ap.add_argument("--data", default="working/team_data.json")
    ap.add_argument("--config", default="config/team_config.json")
    main(ap.parse_args())

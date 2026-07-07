#!/usr/bin/env python3
"""
format_member_message.py — turn a computed cowork_roi_data.json into a DE-IDENTIFIED,
TABLE-FORMATTED Teams channel message (HTML body) for the team Cowork ROI rollup.

v3 (table layout): the post is rendered as HTML <table>s — both human-readable in Teams AND
easy for a downstream Cowork task to parse deterministically (one row per item, stable headers).
It surfaces the full research-grade detail already present in cowork_roi_data.json:

  Headline · Where the time went (band/tasks/hours/value/%) · Business value pillars ·
  Jobs to be done · Work by business process · Roles (hours+value) · Skills (deliverables/sessions/
  value) · Analyzed→Produced (+inputs/outputs by type) · Deliverables & the skills behind them by
  type · Activity by day.

Privacy: NO person / display names, no raw file names, no prompts. Every section is an aggregate
(counts, types, categories, processes, JTBDs) — process/JTBD text may carry customer/account names
(in scope), but nothing identifies a person or a specific file.

Usage:  python format_member_message.py --in working/cowork_roi_data.json \
                                        --out working/member_message.html
Prints the HTML body to stdout between BEGIN/END markers for PostChannelMessage(body=...).
"""
import json, argparse, collections, html

MARK_B = "<<<COWORK-ROI-MEMBER-MESSAGE>>>"
MARK_E = "<<<END>>>"

PILLAR_ORDER = ["Revenue Growth", "Cost Reduction", "Risk Mitigation", "Transformation"]


def esc(s):
    return html.escape(str(s))


def table(headers, rows):
    """Build a parser-stable HTML table. Cells are escaped; headers left-aligned."""
    head = "<tr>" + "".join(f"<th align='left'>{esc(h)}</th>" for h in headers) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return ('<table border="1" cellpadding="4" cellspacing="0" '
            f'style="border-collapse:collapse">{head}{body}</table>')


def hdr(text):
    return f"<p><b>{text}</b></p>"


def build_message(d):
    m = d["meta"]; k = d["kpis"]; val = d["value"]; win = m["window"]
    rate = val.get("hourly_rate") or m.get("hourly_rate_default", 72)
    goals = d.get("goals", [])
    cats = d.get("categories", [])
    roles = d.get("roles", [])
    procs = d.get("processes", [])
    skills_aug = d.get("skills_augmented", [])
    delivs = d.get("deliverables", [])
    io = d.get("io", {})
    heat = d.get("heatmap", [])

    def money(v):
        try:
            return f"${round(v):,}"
        except Exception:
            return f"${v}"

    # ----- pillars / JTBD: roll up sessions + expert minutes from the per-session goals -----
    def agg_by(keyfn):
        mins = collections.defaultdict(float)
        sess = collections.Counter()
        for g in goals:
            mt = g.get("minutes_typical", 0)
            if mt <= 0:
                continue
            key = keyfn(g)
            if not key:
                continue
            mins[key] += mt
            sess[key] += 1
        return mins, sess

    pil_min, pil_sess = agg_by(lambda g: g.get("value_pillar", "Transformation"))
    jtbd_min, jtbd_sess = agg_by(lambda g: (g.get("jtbd") or "").strip())
    total_min = sum(pil_min.values()) or 1

    # ----- real cost (only where measured via /cost) -----
    cov = [g for g in goals if isinstance(g.get("cost_usd"), (int, float))]
    real_cost = sum(g["cost_usd"] for g in cov)
    real_cred = sum(g["credits"] for g in cov if isinstance(g.get("credits"), (int, float)))
    n_total = len([g for g in goals if g.get("minutes_typical", 0) > 0]) or k.get("sessions", 0)

    H = []
    _from = str(win.get('from', ''))[:10]; _to = str(win.get('to', ''))[:10]
    # Runner's directory Role (job title) — de-identified attribute; no country, no name.
    role = (m.get("role") or "").strip()
    role_line = f"<br>Role: {esc(role)}" if role else ""
    H.append(f"<p><b>📊 Cowork ROI — team stats</b><br>Period: {esc(win['label'])} "
             f"({esc(_from)} → {esc(_to)}){role_line}</p>")

    # 1) Headline ------------------------------------------------------------
    # Metric names kept identical to the Copilot ROI Report skill (build_report.py).
    head_rows = [
        ("Expert-equivalent hours", f"{k['hours_saved_typical']} h "
                                    f"(range {val.get('hours_low','?')}–{val.get('hours_high','?')} h)"),
        ("Professional-services value", f"{money(val['value_typical'])} (typical)"),
        ("Speed multiplier", f"{k['speed_multiplier']}×"),
        ("Assisted (hands-on) hours", f"{val.get('exec_hours','?')} h"),
        ("Sessions", k.get('sessions', 0)),
        ("Run tasks", k.get('run_tasks', 0)),
        ("Deliverables", k.get('artifacts', 0)),
        ("Active days", k.get('active_days', 0)),
        ("Hours / active day", k.get('hours_per_active_day', 0)),
    ]
    if real_cost:
        head_rows.append(("Real Cowork cost",
                          f"${real_cost:,.2f} ({real_cred:,.0f} credits, "
                          f"measured on {len(cov)}/{n_total} sessions)"))
    H.append(hdr("⏱️ Headline"))
    H.append(table(["Metric", "Value"], head_rows))

    # 2) Where the time went — by task category ------------------------------
    cat_total_min = sum(c.get("minutes_typical", 0) for c in cats) or 1
    cat_rows = []
    for c in sorted([c for c in cats if c.get("hours_typical", 0) > 0 or c.get("tasks", 0) > 0],
                    key=lambda c: -c.get("hours_typical", 0)):
        band = f"{c.get('low_per_task','?')} / {c.get('typical_per_task','?')} / {c.get('high_per_task','?')}"
        pct = round(100 * c.get("minutes_typical", 0) / cat_total_min)
        cat_rows.append((c["label"], band, c.get("tasks", 0),
                         f"{c.get('hours_typical', 0)} h", money(c.get("value_typical", 0)), f"{pct}%"))
    if cat_rows:
        H.append(hdr("🕒 Where the time went — by task category"))
        H.append(table(["Category", "Band (min low/typ/high)", "Tasks", "Hours", "Value", "% time"], cat_rows))

    # 3) Business value pillars ----------------------------------------------
    pil_rows = []
    for p in sorted(pil_min, key=lambda p: (PILLAR_ORDER.index(p) if p in PILLAR_ORDER else 9, -pil_min[p])):
        mins = pil_min[p]
        pil_rows.append((p, pil_sess[p], f"{round(mins/60,1)} h",
                         money(mins/60*rate), f"{round(100*mins/total_min)}%"))
    if pil_rows:
        H.append(hdr("💼 Business value pillars"))
        H.append(table(["Pillar", "Sessions", "Hours", "Value", "% time"], pil_rows))

    # 4) Jobs to be done -----------------------------------------------------
    jtbd_rows = [(j, jtbd_sess[j], f"{round(jtbd_min[j]/60,1)} h", money(jtbd_min[j]/60*rate))
                 for j in sorted(jtbd_min, key=lambda j: -jtbd_min[j])]
    if jtbd_rows:
        H.append(hdr("✅ Jobs to be done"))
        H.append(table(["Job to be done", "Sessions", "Hours", "Value"], jtbd_rows))

    # 5) Work by business process --------------------------------------------
    proc_total = sum(p.get("minutes_typical", 0) for p in procs) or 1
    proc_rows = []
    for p in sorted(procs, key=lambda p: -p.get("minutes_typical", 0)):
        pct = p.get("pct_time", round(100 * p.get("minutes_typical", 0) / proc_total))
        proc_rows.append((p["process"], p.get("sessions", 0), f"{p.get('hours_typical', 0)} h",
                          money(p.get("value_typical", 0)), f"{pct}%"))
    if proc_rows:
        H.append(hdr("🏭 Work by business process"))
        H.append(table(["Process", "Sessions", "Hours", "Value", "% time"], proc_rows))

    # 6) Roles Cowork stood in for (hours + value) ---------------------------
    role_rows = [(r["role"], f"{r.get('hours', 0)} h", money(r.get("value", 0)))
                 for r in roles if r.get("hours", 0) >= 0.1]
    if role_rows:
        H.append(hdr("🧑‍💼 Roles Cowork assembled for me"))
        H.append(table(["Role", "Hours", "Value"], role_rows))

    # 7) Skills applied (deliverables / sessions / value) --------------------
    skill_rows = [(s["skill"], s.get("deliverables", 0), s.get("sessions", 0), money(s.get("value", 0)))
                  for s in skills_aug]
    if skill_rows:
        H.append(hdr("🛠️ Skills applied"))
        H.append(table(["Skill", "Deliverables", "Sessions", "Value"], skill_rows))

    # 8) Analyzed → Produced + inputs/outputs by type ------------------------
    if io:
        H.append(hdr("🔄 Analyzed → Produced"))
        H.append(table(["Measure", "Value"], [
            ("Inputs analyzed", io.get("inputs_total", 0)),
            ("Outputs produced", io.get("outputs_total", 0)),
            ("Sources / deliverable", io.get("per_deliverable", "—")),
        ]))
        if io.get("inputs_by_type"):
            H.append(hdr("Inputs by type"))
            H.append(table(["Input type", "Count"],
                           [(t["label"], t["count"]) for t in io["inputs_by_type"]]))
        if io.get("outputs_by_type"):
            H.append(hdr("Outputs by type"))
            H.append(table(["Output type", "Count"],
                           [(t["label"], t["count"]) for t in io["outputs_by_type"]]))

    # 9) Deliverables & the skills behind them -------------------------------
    #    Every deliverable is made visible (type + date), labelled with the
    #    business process it supported — de-identified: NO file names.
    if delivs:
        H.append(hdr("📦 Deliverables &amp; the skills behind them"))
        per_rows = []
        for dv in sorted(delivs, key=lambda x: -x.get("value", 0)):
            per_rows.append((dv.get("type", "File"), dv.get("date", ""),
                             dv.get("process", "—"),
                             ", ".join(s for s in dv.get("skills", []) if s) or "—",
                             f"{dv.get('hours', 0)} h", money(dv.get("value", 0))))
        H.append(table(["Type", "Date", "Business process", "Skills", "Hours", "Value"], per_rows))

        # by-type rollup (kept — compact summary, also what the aggregated Dashboard reads)
        by_type = collections.OrderedDict()
        for dv in delivs:
            t = dv.get("type", "File")
            acc = by_type.setdefault(t, {"count": 0, "hours": 0.0, "value": 0, "skills": set()})
            acc["count"] += 1
            acc["hours"] += dv.get("hours", 0)
            acc["value"] += dv.get("value", 0)
            acc["skills"].update(s for s in dv.get("skills", []) if s)
        deliv_rows = [(t, a["count"], f"{round(a['hours'],1)} h", money(a["value"]),
                       ", ".join(sorted(a["skills"])) or "—")
                      for t, a in sorted(by_type.items(), key=lambda kv: -kv[1]["hours"])]
        H.append(hdr("By type"))
        H.append(table(["Deliverable type", "Count", "Hours", "Value", "Skills used"], deliv_rows))

    # 10) Activity by day ----------------------------------------------------
    day = collections.Counter()
    for h in heat:
        day[h.get("date", "?")] += h.get("count", 0)
    if day:
        H.append(hdr("📅 Activity by day"))
        H.append(table(["Date", "Run tasks"], [(dte, day[dte]) for dte in sorted(day)]))

    H.append('<p style="font-size:12px;color:#605E5C">Methodology: research-anchored per-category '
             'time bands × run tasks; value = expert hours × hourly rate; speed multiplier is '
             'directional (expert ÷ modeled assisted clock). De-identified — person names, file '
             'names, prompts and country excluded; the runner\'s directory role is shown. '
             'Generated by the Cowork ROI member skill.</p>')
    return "".join(H)


def main(inp, out):
    d = json.load(open(inp))
    body = build_message(d)
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    print(MARK_B)
    print(body)
    print(MARK_E)
    print(f"\n[wrote {out} · {len(body)} chars]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/cowork_roi_data.json")
    ap.add_argument("--out", default="working/member_message.html")
    a = ap.parse_args()
    main(a.inp, a.out)

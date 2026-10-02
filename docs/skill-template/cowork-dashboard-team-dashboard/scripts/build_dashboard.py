#!/usr/bin/env python3
"""
build_dashboard.py — render team_data.json (from parse_posts.py) into a single
self-contained, team-safe HTML dashboard.

The input JSON is a private working intermediate. Before rendering, the builder drops
contributor records and emits only aggregate breakdowns supported by >= kThreshold people.
It never embeds task-level entries, deliverable names, or role assignments.

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
import json, argparse, os, re


CATEGORIES = {
    "Analysis & Research", "Write or debug code", "Document & content creation",
    "Meeting workflows", "Specialized workflows", "General assistance / Other",
    "Email workflows", "Communication workflows",
}
FORMATS = {
    "deck": "PPTX", "slides": "PPTX", "presentation": "PPTX",
    "slide deck": "PPTX", "document": "Word", "doc": "Word", "word": "Word",
    "spreadsheet": "Excel / CSV", "excel": "Excel / CSV", "csv": "Excel / CSV",
    "web page": "HTML", "webpage": "HTML", "web": "HTML", "html": "HTML",
    "text": "Text / MD", "markdown": "Text / MD", "image": "Image",
    "pdf": "PDF", "file": "File (other)",
}
GRADES = {"H", "M", "L"}


def number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if value != value or abs(value) == float("inf"):
        return 0
    value = max(0, value)
    return int(value) if value.is_integer() else value


def public_data(data):
    """Build a cohort-filtered public contract; never serialize contributor records."""
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    try:
        threshold = max(2, int(meta.get("kThreshold", 3)))
    except (TypeError, ValueError, OverflowError):
        threshold = 3

    def read_json(name):
        path = os.path.join(os.path.dirname(__file__), name)
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    processes = set(read_json("process_groups.json").get("groups", []))
    roles = {
        item["role"] for item in read_json("roles_taxonomy.json").get("roles", [])
        if isinstance(item, dict) and item.get("role")
    }
    skills_data = read_json("skills_vocabulary.json")
    skills = {
        item["name"]
        for key in ("domain_skills", "tech_skills")
        for item in skills_data.get(key, [])
        if isinstance(item, dict) and item.get("name")
    }
    category_aliases = {
        "email": "Email workflows", "email workflow": "Email workflows",
        "communication": "Communication workflows", "specialized": "Specialized workflows",
        "general assistance": "General assistance / Other", "other": "General assistance / Other",
    }
    process_lookup = {process.casefold(): process for process in processes}
    role_lookup = {role.casefold(): role for role in roles}
    skill_lookup = {skill.casefold(): skill for skill in skills}

    def safe_role(value):
        return role_lookup.get(value.casefold(), "Other role") if isinstance(value, str) else "Other role"

    def safe_process(value):
        return process_lookup.get(value.casefold(), "Other process") if isinstance(value, str) else "Other process"

    def safe_skill(value):
        return skill_lookup.get(value.casefold(), "Other skill") if isinstance(value, str) else "Other skill"

    def safe_category(value):
        if not isinstance(value, str):
            return "General assistance / Other"
        if value in CATEGORIES:
            return value
        return category_aliases.get(value.casefold(), "General assistance / Other")

    def safe_process_with_unknown(value):
        process = safe_process(value)
        return process if process != "Other process" else "General Productivity"

    def safe_format(value):
        return FORMATS.get(str(value or "").strip().lower(), "Other format")

    def empty_metric(fields):
        return {"contributors": set(), **{field: 0.0 for field in fields}}

    def aggregate(ids):
        rows = {
            "categories": {}, "processes": {}, "roles": {}, "skills": {},
            "deliverables": {}, "processDetails": {}, "fit": {}, "fitDetails": {},
            "inputs": {}, "outputs": {}, "roleGroups": {},
        }
        head = {key: 0.0 for key in (
            "timeTyp", "timeLow", "timeHigh", "expertH", "assistedH", "sessions",
            "runTasks", "deliverables", "activeDays",
        )}
        low_count = high_count = 0
        contributors = set()

        def add(metric, key, fields, source, member_id):
            if not isinstance(source, dict):
                return
            values = {field: number(source.get(field)) for field in fields}
            item = metric.setdefault(key, empty_metric(fields))
            if any(value > 0 for value in values.values()):
                item["contributors"].add(member_id)
            for field in fields:
                item[field] += values[field]

        private_members = data.get("members", [])
        if not isinstance(private_members, list):
            private_members = []
        for member_index, member in enumerate(private_members):
            if not isinstance(member, dict):
                continue
            reports = member.get("reports", {})
            if not isinstance(reports, dict):
                continue
            selected = [reports[period_id] for period_id in ids if isinstance(reports.get(period_id), dict)]
            if not selected:
                continue
            member_id = member_index
            contributors.add(member_id)
            role_group = safe_role(member.get("role"))
            role_group_data = rows["roleGroups"].setdefault(
                role_group, {"contributors": set(), "categories": {}}
            )
            role_group_data["contributors"].add(member_id)

            for report in selected:
                headline = report.get("headline", {})
                for field in head:
                    if field in ("timeLow", "timeHigh"):
                        continue
                    head[field] += number(headline.get(field))
                if headline.get("timeLow") is not None:
                    head["timeLow"] += number(headline.get("timeLow"))
                    low_count += 1
                if headline.get("timeHigh") is not None:
                    head["timeHigh"] += number(headline.get("timeHigh"))
                    high_count += 1

                for item in (report.get("categories", []) if isinstance(report.get("categories"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    name = safe_category(item.get("name"))
                    add(rows["categories"], name, ("tasks", "hours"), item, member_id)
                    role_cat = role_group_data["categories"].setdefault(
                        name, {"contributors": set(), "hours": 0.0}
                    )
                    if number(item.get("tasks")) > 0 or number(item.get("hours")) > 0:
                        role_cat["contributors"].add(member_id)
                        role_cat["hours"] += number(item.get("hours"))

                for item in (report.get("processes", []) if isinstance(report.get("processes"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    add(rows["processes"], safe_process_with_unknown(item.get("name")),
                        ("sessions", "hours"), item, member_id)
                for item in (report.get("roles", []) if isinstance(report.get("roles"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    add(rows["roles"], safe_role(item.get("name")), ("hours",), item, member_id)
                for item in (report.get("skills", []) if isinstance(report.get("skills"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    add(rows["skills"], safe_skill(item.get("name")),
                        ("deliverables", "sessions", "hours"), item, member_id)
                for item in (report.get("deliverables", []) if isinstance(report.get("deliverables"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    add(rows["deliverables"], safe_format(item.get("type")),
                        ("count", "hours"), item, member_id)
                for item in (report.get("deliverablesDetail", []) if isinstance(report.get("deliverablesDetail"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    process = safe_process_with_unknown(item.get("process"))
                    fmt = safe_format(item.get("type"))
                    key = (process, fmt)
                    add(rows["processDetails"], key, ("count", "hours"), {
                        "count": 1, "hours": item.get("hours"),
                    }, member_id)
                    detail = rows["processDetails"][key]
                    if "skills" not in detail:
                        detail["skills"] = {}
                    item_skills = item.get("skills", [])
                    for skill in (set(safe_skill(value) for value in item_skills if isinstance(value, str))
                                  if isinstance(item_skills, list) else ()):
                        entry = detail["skills"].setdefault(
                            skill, {"contributors": set(), "count": 0}
                        )
                        entry["contributors"].add(member_id)
                        entry["count"] += 1
                for item in (report.get("coworkFit", []) if isinstance(report.get("coworkFit"), list) else []):
                    if not isinstance(item, dict):
                        continue
                    grade = item.get("grade")
                    if grade not in GRADES:
                        continue
                    add(rows["fit"], grade, ("count", "hours"), {
                        "count": 1, "hours": item.get("hours"),
                    }, member_id)
                    category = safe_category(item.get("category"))
                    key = (grade, safe_process_with_unknown(item.get("process")), category)
                    add(rows["fitDetails"], key, ("count", "hours"), {
                        "count": 1, "hours": item.get("hours"),
                    }, member_id)
                io = report.get("io", {})
                if not isinstance(io, dict):
                    io = {}
                for source_key, target_key in (("inputs", "inputs"), ("outputs", "outputs")):
                    source_items = io.get(source_key, [])
                    for item in source_items if isinstance(source_items, list) else ():
                        if not isinstance(item, dict):
                            continue
                        add(rows[target_key], safe_format(item.get("type")), ("count",), item, member_id)

        head["timeLow"] = head["timeLow"] if low_count else head["timeTyp"]
        head["timeHigh"] = head["timeHigh"] if high_count else head["timeTyp"]

        def exposed(metric, names):
            result = []
            for key, item in metric.items():
                if len(item["contributors"]) < threshold:
                    continue
                row = {name: key if name == "name" else item.get(name, 0) for name in names}
                row["contributors"] = len(item["contributors"])
                result.append(row)
            return result

        categories = exposed(rows["categories"], ("name", "tasks", "hours"))
        processes_out = exposed(rows["processes"], ("name", "sessions", "hours"))
        roles_out = exposed(rows["roles"], ("name", "hours"))
        skills_out = exposed(rows["skills"], ("name", "deliverables", "sessions", "hours"))
        deliverables_out = exposed(rows["deliverables"], ("name", "count", "hours"))
        details_out = []
        for (process, fmt), item in rows["processDetails"].items():
            if len(item["contributors"]) < threshold:
                continue
            visible_skills = [
                {"name": name, "count": value["count"],
                 "contributors": len(value["contributors"])}
                for name, value in item.get("skills", {}).items()
                if len(value["contributors"]) >= threshold
            ]
            details_out.append({
                "process": process, "type": fmt, "count": item["count"],
                "hours": item["hours"], "contributors": len(item["contributors"]),
                "skills": visible_skills,
            })

        fit_out = exposed(rows["fit"], ("name", "count", "hours"))
        fit_out = [{"grade": item["name"], "count": item["count"],
                    "hours": item["hours"], "contributors": item["contributors"]}
                   for item in fit_out]
        fit_details_out = [
            {"grade": key[0], "process": key[1], "category": key[2],
             "count": item["count"], "hours": item["hours"],
             "contributors": len(item["contributors"])}
            for key, item in rows["fitDetails"].items()
            if len(item["contributors"]) >= threshold
        ]

        role_groups = []
        pooled_members = set()
        for name, item in rows["roleGroups"].items():
            if len(item["contributors"]) < threshold:
                pooled_members.update(item["contributors"])
                continue
            role_groups.append({
                "name": name, "contributors": len(item["contributors"]),
                "categories": [
                    {"name": cat, "hours": value["hours"],
                     "contributors": len(value["contributors"])}
                    for cat, value in item["categories"].items()
                    if len(value["contributors"]) >= threshold
                ],
            })
        if len(pooled_members) >= threshold:
            role_groups.append({"name": "Other roles (combined)",
                                "contributors": len(pooled_members), "categories": []})

        def expose_formats(metric):
            return exposed(metric, ("name", "count"))

        return {
            "contributors": len(contributors), "head": head, "categories": categories,
            "processes": processes_out, "roles": roles_out, "skills": skills_out,
            "deliverables": deliverables_out, "processDetails": details_out,
            "fit": fit_out, "fitDetails": fit_details_out, "roleGroups": role_groups,
            "inputs": expose_formats(rows["inputs"]), "outputs": expose_formats(rows["outputs"]),
            "kThreshold": threshold,
        }

    def safe_date(value):
        return value if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None

    public_snapshots = []
    private_snapshot_ids = []
    aggregate_by_id = {}
    snapshots = data.get("snapshots", [])
    if not isinstance(snapshots, list):
        snapshots = []
    for index, snapshot in enumerate(snapshots, 1):
        if not isinstance(snapshot, dict):
            continue
        private_id = str(snapshot.get("id", ""))
        public_id = private_id if safe_date(private_id) else f"snapshot-{index}"
        label = str(snapshot.get("label", ""))
        if not re.fullmatch(r"Last \d{1,3} days|All time|Current period", label, re.I):
            label = "Reporting period"
        public_snapshots.append({
            "id": public_id,
            "label": label,
            "periodStart": safe_date(snapshot.get("periodStart")),
            "periodEnd": safe_date(snapshot.get("periodEnd")),
            "postedDate": safe_date(snapshot.get("postedDate")),
        })
        private_snapshot_ids.append(private_id)
        aggregate_by_id[public_id] = aggregate([private_id])
    aggregate_by_id["ALL"] = aggregate(private_snapshot_ids)
    return {
        "meta": {
            "team": str(meta.get("team") or "Team"),
            "generated": safe_date(meta.get("generated")) or "",
            "defaultRate": number(meta.get("defaultRate", 72)),
            "defaultRecapture": min(1, max(0, number(meta.get("defaultRecapture", 0.70)))),
            "kThreshold": threshold,
        },
        "snapshots": public_snapshots,
        "aggregates": aggregate_by_id,
    }


def json_for_html(value):
    """Keep JSON data inside its script element, even when untrusted text contains </script>."""
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def escape_html(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))

CSS = r"""
:root{--bg:#f3f4f8;--panel:#fff;--ink:#1f2329;--muted:#5d6470;--faint:#8a909c;--line:#e4e7ee;
--brand:#0f6cbd;--brand-d:#0b5394;--soft:#eaf3fb;--good:#107c10;--shadow:0 1px 2px rgba(16,24,40,.06),0 4px 16px rgba(16,24,40,.06);
/* Analyzed -> Produced (input/output columns) — two colors NOT in the task category palette: a warm amber-GOLD (not olive) for inputs analyzed, magenta for outputs produced. Keeps this section distinct from the task categories. */
--io-in:#d99c1e;--io-out:#b4009e;
--c0:#0f6cbd;--c1:#2e8b57;--c2:#ca5010;--c3:#8764b8;--c4:#0099bc;--c5:#c4314b;--c6:#7a7574;--c7:#498205;--donut-edge:rgba(0,0,0,.16);}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--panel:#1f2228;--ink:#e9ebef;--muted:#a7adb8;--faint:#7c828d;--line:#2c3038;--brand:#4aa3e8;--brand-d:#74b9ee;--soft:#1b2a39;--shadow:0 1px 2px rgba(0,0,0,.4);--donut-edge:rgba(255,255,255,.26);}}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45;-webkit-font-smoothing:antialiased}
.wrap{max-width:1140px;margin:0 auto;padding:0 20px 60px}
header.top{background:linear-gradient(120deg,var(--brand-d),var(--brand));color:#fff;padding:24px 0 18px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:9px}.brand .nm{font-size:13px;letter-spacing:.3px;opacity:.92;font-weight:600}
header.top h1{font-size:26px;margin:2px 0 4px;font-weight:700;letter-spacing:-.2px}
header.top .sub{font-size:14px;opacity:.93;margin:0}header.top .gen{font-size:12px;opacity:.82;margin-top:7px}
header.top .disc{font-size:11px;line-height:1.45;opacity:.9;margin:10px 0 0;max-width:940px}header.top .disc b{font-weight:700}
.banner{background:#fff7e6;border:1px solid #f3d98b;color:#7a5b00;border-radius:10px;padding:10px 14px;font-size:12.5px;margin:16px 0 0;display:flex;gap:9px;align-items:flex-start}
@media (prefers-color-scheme:dark){.banner{background:#332a12;border-color:#5c4a17;color:#e8cf8f}}
.controls{position:sticky;top:0;z-index:30;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:13px 16px;margin:16px 0 0;display:flex;flex-wrap:wrap;gap:14px 24px;align-items:flex-end}
.ctl{display:flex;flex-direction:column;gap:6px}.ctl label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--faint);font-weight:700}
.ctl select,.ctl input{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:150px}
.rate-in{display:flex;align-items:center;gap:6px}.rate-in span{color:var(--faint);font-weight:600}.rate-in input{width:82px;min-width:70px}
.btn{font:inherit;font-size:13px;font-weight:600;padding:8px 14px;border-radius:8px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.btn.primary{background:var(--brand);border-color:var(--brand);color:#fff}.btn:hover{border-color:var(--brand)}.spacer{flex:1 1 auto}
.tabs{position:sticky;top:0;z-index:25;display:flex;gap:4px;flex-wrap:wrap;margin:16px 0 8px;border-bottom:2px solid var(--line);background:var(--bg)}
.tab-btn{font:inherit;font-size:13.5px;font-weight:600;padding:11px 15px;border:none;background:none;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tab-btn.on{color:var(--brand);border-bottom-color:var(--brand)}.tab-btn:hover{color:var(--ink)}
.tab-panel{display:none}.tab-panel.on{display:block}
section.block{margin:24px 0 0;scroll-margin-top:120px}
h2.sec{font-size:16px;font-weight:700;margin:0 0 3px;display:flex;align-items:center;gap:9px;position:relative;flex-wrap:wrap}
h2.sec .dot{width:9px;height:9px;border-radius:3px;background:var(--brand)}
.sec-note{font-size:12.5px;color:var(--muted);margin:0 0 13px}
/* Click-to-reveal "?" helper next to a section title — a short plain-language explanation, in-page. */
.help{width:17px;height:17px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:10.5px;font-weight:700;line-height:1;cursor:pointer;padding:0;display:inline-flex;align-items:center;justify-content:center;flex:none}
.help:hover{border-color:var(--brand);color:var(--brand)}
.helppop{position:absolute;top:28px;inset-inline-start:0;z-index:40;max-width:460px;background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);padding:11px 14px;font-size:12.5px;font-weight:400;color:var(--muted);line-height:1.5;display:none}
.helppop.on{display:block}.helppop b{color:var(--ink);font-weight:650}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .k-l{font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700}
.kpi .k-v{font-size:25px;font-weight:750;margin:5px 0 2px;letter-spacing:-.3px}.kpi .k-s{font-size:12px;color:var(--muted)}
.kpi.hero{background:linear-gradient(135deg,var(--soft),var(--panel));border-color:#cfe3f5}
@media (prefers-color-scheme:dark){.kpi.hero{border-color:#274a68}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px 18px 15px;box-shadow:var(--shadow)}
.card h3{font-size:14px;margin:0 0 4px;font-weight:700}.card .hint{font-size:11.5px;color:var(--faint);margin:0 0 12px}
/* Fixed value column (232px) so the gray track is the SAME length on every row; .rc = count rows (narrow value). */
.row{display:grid;grid-template-columns:180px 1fr 232px;align-items:center;gap:11px;padding:5px 0}
.row.rc{grid-template-columns:180px 1fr 56px}
.row .rl{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .rbar{background:var(--bg);border-radius:6px;height:16px;overflow:hidden}.row .rfill{height:100%;border-radius:6px;min-width:2px}
.row .rv{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}.row .rv b{color:var(--ink);font-weight:650}
table.dt{width:100%;border-collapse:collapse;font-size:13px}
table.dt th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700;padding:8px 10px;border-bottom:2px solid var(--line)}
table.dt th.r,table.dt td.r{text-align:right;font-variant-numeric:tabular-nums}
table.dt td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}table.dt tr:last-child td{border-bottom:none}
table.dt tr.tot td{font-weight:700;border-top:2px solid var(--line);background:var(--bg)}
.catsw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-inline-end:8px;vertical-align:middle;flex:none}
.footnote{font-size:11.5px;color:var(--faint);margin-top:9px;line-height:1.5}.footnote b{color:var(--muted)}
.pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;background:var(--soft);color:var(--brand-d);font-weight:600;margin:1px 3px 1px 0}
.insights{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.ins{display:flex;gap:11px;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:10px;padding:12px 14px;box-shadow:var(--shadow)}
.ins .ic{font-size:18px;line-height:1.2}.ins .tx{font-size:13px}.ins .tx b{font-weight:700}
.ins.insgroup{flex-direction:column;gap:11px}
.insgroup .ig-h{font-size:13px;font-weight:700;color:var(--ink)}
.insgroup .ig-rows{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.insgroup .ig-row{display:flex;gap:9px;align-items:flex-start}
.insgroup .ig-row .ic{font-size:17px;line-height:1.2}.insgroup .ig-row .tx{font-size:12.5px}.insgroup .ig-row .tx b{font-weight:700}
.insgroup .ig-cat{font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700;margin-bottom:3px}
.insgroup .ig-cat.navlink{display:inline-flex;align-items:center;gap:4px;background:none;border:0;padding:0;cursor:pointer;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;font-weight:700;color:var(--faint)}
.insgroup .ig-cat.navlink:hover,.insgroup .ig-cat.navlink:focus-visible{color:var(--ink);text-decoration:underline;text-decoration-style:dotted;text-decoration-color:var(--faint);outline:none}
.insgroup .ig-cat.navlink .ig-arrow{font-size:11px;opacity:.75}
/* Glossary hover tooltip: a term with a dotted underline pops its definition (from the Glossary) on hover/focus. */
.gloss{position:relative;cursor:help;border-bottom:1px dotted currentColor}
.gloss>.gtip{position:absolute;top:calc(100% + 6px);inset-inline-start:0;z-index:70;width:220px;max-width:70vw;background:var(--ink);color:var(--panel);border-radius:8px;padding:8px 10px;font-size:12px;font-weight:400;line-height:1.45;text-transform:none;letter-spacing:normal;box-shadow:var(--shadow);display:none;white-space:normal}
.gloss:hover>.gtip,.gloss:focus>.gtip,.gloss:focus-within>.gtip{display:block}
/* Inline cross-reference link — jumps to the named section/tab. */
.xref{display:inline;background:none;border:0;padding:0;margin:0;font:inherit;color:inherit;cursor:pointer;text-decoration:underline dotted;text-decoration-color:var(--faint);text-underline-offset:2px}
.xref:hover,.xref:focus-visible{text-decoration-color:var(--ink);outline:none}
.insgroup .ig-name{font-size:14px;font-weight:700;color:var(--ink);margin-bottom:1px}
.insgroup .ig-val{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.donut-wrap{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.legend{display:flex;flex-direction:column;gap:7px;font-size:12.5px}.legend .li{display:flex;align-items:center;gap:9px}
.legend .sw{width:12px;height:12px;border-radius:3px;flex:none;box-shadow:inset 0 0 0 1px var(--donut-edge)}.legend .lt{flex:1}.legend .lv{color:var(--muted);font-variant-numeric:tabular-nums}
.stackrow{display:grid;grid-template-columns:200px 1fr;align-items:center;gap:11px;padding:6px 0}
.stackbar{display:flex;height:22px;border-radius:6px;overflow:hidden;background:var(--bg)}.stackseg{height:100%;display:flex;align-items:center;justify-content:center;overflow:hidden}.segpct{font-size:9px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.45);white-space:nowrap;line-height:1}
/* Cowork-fit waterfall: one part-to-whole bar of graded tasks (High/Medium/Low), each an expandable row below. */
.wf-cap{font-size:13px;color:var(--muted);margin:0 0 8px}.wf-cap b{color:var(--ink);font-size:16px;font-weight:750}
.wf-bar{display:flex;height:34px;border-radius:8px;overflow:hidden;background:var(--bg)}
.wf-seg{height:100%;display:flex;align-items:center;justify-content:center}.wf-seg span{font-size:12.5px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.4)}
.wf-leg{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:10px;font-size:12px;color:var(--muted)}
.wf-li{display:inline-flex;align-items:center;gap:6px}
.wf-dot{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.wf-svg{width:100%;height:auto;display:block;overflow:visible;margin:2px 0 4px}
.wf-svg .wfv{font-size:13px;font-weight:750;fill:var(--ink)}
.wf-svg .wfl{font-size:12.5px;font-weight:650;fill:var(--ink)}
.wf-svg .wfs{font-size:11px;fill:var(--muted)}
.wf-svg .wfc{stroke:var(--faint);stroke-width:1;stroke-dasharray:3 3;opacity:.7}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;background:var(--bg)}
.seg-btn{appearance:none;-webkit-appearance:none;border:0;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:650;padding:7px 15px;cursor:pointer}
.seg-btn+.seg-btn{border-inline-start:1px solid var(--line)}
.seg-btn.on{background:var(--c1);color:#fff}
.ov-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px}
.ov-tl{font-size:13px;color:var(--muted);font-weight:650}
.kpi.metric-sel{outline:2px solid var(--c1);outline-offset:1px}
.ranklist{list-style:none;margin:0;padding:0}
.rk-row{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:13px;padding:11px 4px;border-bottom:1px solid var(--line)}
.rk-row:last-child{border-bottom:none}
.rk-badge{width:25px;height:25px;border-radius:50%;background:var(--bg);border:1px solid var(--line);color:var(--c0);font-weight:750;font-size:12.5px;display:flex;align-items:center;justify-content:center;flex:none}
.rk-nm{font-weight:600;font-size:14px}
.rk-v{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.rk-v b{color:var(--ink)}
.io2{display:grid;grid-template-columns:1fr 1fr;gap:26px}.io2 h4{font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);margin:0 0 10px}
.svgtrend{width:100%;height:150px}.trend-empty{font-size:12.5px;color:var(--muted);margin-top:8px}
details.meth{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);margin-bottom:12px;scroll-margin-top:120px}
details.meth summary{cursor:pointer;padding:14px 18px;font-weight:700;font-size:14px;list-style:none}
details.meth summary::-webkit-details-marker{display:none}
details.meth summary::before{content:'\25B8';margin-inline-end:9px;color:var(--brand);display:inline-block;transition:.15s}
details.meth[open] summary::before{transform:rotate(90deg)}
details.meth .mbody{padding:0 18px 16px;font-size:13px;color:var(--muted)}details.meth .mbody h4{color:var(--ink);font-size:13px;margin:13px 0 5px}details.meth a{color:var(--brand)}
details.meth .mbody ul{margin:4px 0 12px;padding-inline-start:20px}details.meth .mbody li{margin:3px 0}
details.drill{margin-top:13px;border-top:1px dashed var(--line);padding-top:9px}
details.drill>summary{cursor:pointer;font-size:12.5px;font-weight:650;color:var(--brand);list-style:none;user-select:none}
details.drill>summary::-webkit-details-marker{display:none}
details.drill>summary::before{content:'\25B8';margin-inline-end:7px;display:inline-block;transition:.15s;color:var(--brand)}
details.drill[open]>summary::before{transform:rotate(90deg)}
details.drill .dbody{padding-top:11px}
.dgrp{margin:0 0 15px}.dgrp .dgrp-h{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px;margin:0 0 5px}
/* Expandable business-process accordion (each row opens to its deliverable formats + skills). */
.acct{border:1px solid var(--line);border-radius:11px;overflow:hidden}
.acct-h,.acct-tot,.acct-row>summary{display:grid;grid-template-columns:1fr 96px 92px 72px;gap:10px;align-items:center;padding:10px 14px;font-size:13px}
.acct-h{background:var(--bg);font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--faint);font-weight:700}
.acct-h .r,.acct-row>summary .r,.acct-tot .r{text-align:right;font-variant-numeric:tabular-nums}
.acct-row{border-top:1px solid var(--line)}
.acct-row>summary{cursor:pointer;list-style:none;user-select:none}
.acct-row>summary::-webkit-details-marker{display:none}
.acct-row>summary .ap{position:relative;padding-inline-start:17px;font-weight:600}
.acct-row>summary .ap::before{content:'\25B8';position:absolute;inset-inline-start:0;top:0;color:var(--brand);transition:transform .15s}
.acct-row[open]>summary .ap::before{transform:rotate(90deg)}
.acct-row[open]>summary{background:var(--soft)}
.acct-row>.acct-body{padding:13px 14px 15px;background:var(--bg);border-top:1px dashed var(--line)}
.acct-tot{border-top:2px solid var(--line);background:var(--bg);font-weight:700}
.skline{margin-top:11px;font-size:12.5px}.skline .sklbl{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;color:var(--faint);margin:0 8px 4px 0}
details.drill.sub{margin-top:11px;border-top:1px dashed var(--line);padding-top:9px}details.drill.sub>summary{font-size:12px}
/* Flattened per-process deliverable list: distinct deliverables, one level indented, format inline. */
.dlv-list{margin-inline-start:16px;border-inline-start:2px solid var(--line);padding-inline-start:12px}
.dlv{display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid var(--line)}
.dlv:last-child{border-bottom:none}
.dlv-nm{font-size:13px;overflow:hidden;text-overflow:ellipsis}
.fmt-tag{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;color:var(--brand-d);background:var(--soft);border-radius:6px;padding:2px 8px;white-space:nowrap}
.dlv-v{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
@media (max-width:860px){.acct-h,.acct-tot,.acct-row>summary{grid-template-columns:1fr 56px 66px 52px;gap:6px;font-size:12px}}
footer.foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--faint)}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2,.io2,.insights{grid-template-columns:1fr}.insgroup .ig-rows{grid-template-columns:1fr}.row{grid-template-columns:118px 1fr 132px}.row.rc{grid-template-columns:118px 1fr 46px}.row .rv{white-space:normal}.stackrow{grid-template-columns:120px 1fr}.helppop{max-width:78vw}}
@media print{body{background:#fff}.controls,.banner,.tabs{display:none}.tab-panel{display:block!important}
.card,.kpi,details.meth{box-shadow:none;border-color:#ccc}details.meth summary{display:none}details.meth .mbody{display:block!important}
details.drill .dbody{display:block!important}.acct-row>.acct-body{display:block!important}
header.top{background:var(--brand)!important}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}section.block{break-inside:avoid}}
"""

JS = open(os.path.join(os.path.dirname(__file__), "dashboard_runtime.js"), encoding="utf-8").read()

TEMPLATE = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">
<title>Cowork Team Dashboard</title>
<style>__CSS__</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><svg width="22" height="22" viewBox="0 0 23 23" aria-hidden="true"><rect x="1" y="1" width="10" height="10" fill="#F25022"></rect><rect x="12" y="1" width="10" height="10" fill="#7FBA00"></rect><rect x="1" y="12" width="10" height="10" fill="#00A4EF"></rect><rect x="12" y="12" width="10" height="10" fill="#FFB900"></rect></svg><span class="nm">Microsoft Copilot Cowork</span></div>
  <h1>Cowork Team Dashboard</h1>
  <p class="sub">__TEAM__ Impact &amp; how Cowork is used</p>
  <p class="gen">Generated __GENERATED__ · <span id="ctxline"></span></p>
  <p class="disc">Use the information in this report to gauge the impact of Cowork on your team, <b>not as individual or team performance scores</b>. Treat these as directional estimates of tool-assisted time savings, and read them with team context in mind (e.g., project phase, seasonality). Anonymized &amp; team-level only: nothing is shown per person.</p>
  <p class="disc" style="margin-top:7px">New to this report? The <button type="button" class="xref" data-goto="method"><i>How to read + Glossary</i></button> tab explains every number, tab and control &mdash; and every section title has a clickable <b>?</b> for a quick explanation.</p>
  <p class="disc" style="margin-top:7px">Use the <b>Period selector, Hourly rate box, and Recapture rate box</b> below to pick the reporting window, the hourly rate (default $__RATE__/hr), and the productivity recapture rate (default __RECAP__%). Value / cost-reduction figures = effective recaptured hours × hourly rate and recompute instantly; time-saved hours and counts stay the same.</p>
</div></header>
<div class="wrap">
  <div class="controls">
    <div class="ctl"><label for="snapSel">Period</label><select id="snapSel"></select></div>
    <div class="ctl"><label for="rateInput">Hourly rate</label><div class="rate-in"><span>$</span><input id="rateInput" type="number" min="1" step="1" inputmode="numeric"><span>/hr</span></div></div>
    <div class="ctl"><label for="recapInput">Recapture rate</label><div class="rate-in"><input id="recapInput" type="number" min="0" max="100" step="5" inputmode="numeric"><span>%</span></div></div>
    <div class="ctl"><label>Show impact as</label><div class="seg" id="ovSeg" role="group" aria-label="Show impact as Assisted Time or Assisted Value"><button type="button" class="seg-btn on" data-metric="time">Assisted Time</button><button type="button" class="seg-btn" data-metric="value">Assisted Value</button></div></div>
    <div class="spacer"></div>
    <button class="btn" id="resetBtn" type="button">Reset</button>
    <button class="btn primary" id="printBtn" type="button">Save / Print PDF</button>
  </div>
  <div class="tabs">
    <button class="tab-btn on" type="button" data-tab="overview">Overview</button>
    <button class="tab-btn" type="button" data-tab="impact">Impact &amp; Value</button>
    <button class="tab-btn" type="button" data-tab="work">How Cowork is used</button>
    <button class="tab-btn" type="button" data-tab="method" style="font-style:italic">How to read + Glossary</button>
  </div>

  <div class="tab-panel on" id="tab-overview">
    <section class="block"><h2 class="sec"><span class="dot"></span>What the data says<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">A plain-language reading of the team's posts, generated automatically. It re-words itself when you change the hourly rate below.</span></h2><p class="sec-note">The four highlights below summarize the team's Cowork impact at a glance: the total time reclaimed and its dollar value, the task category driving the most savings, the business process where Cowork is applied most, and the type of business value it advances most — so you can quickly see where the impact is concentrated.</p><div class="insights" id="ov-insights"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Team impact at a glance<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The headline totals for the selected period. <b>Value</b> = manual hours &times; the hourly rate in the control bar, so it recomputes whenever you change the rate.</span></h2><div class="kpis" id="ov-kpis"></div><p class="sec-note" style="margin-top:12px"><b>About the ranges:</b> under <b>Time saved</b> and <b>Value / cost reduction</b> the headline is the typical (mid-point) estimate; the low&ndash;high range beside it is the conservative-to-optimistic span from the research time bands (each task category carries a low / typical / high band &mdash; see <button type="button" class="xref" data-goto="method" data-scroll="sec-bands"><i>How to read</i></button>).</p></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Where Cowork is applied — top business processes<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The business processes the team uses Cowork for most, ranked by the selected measure (time saved or value). Process and detail breakdowns appear only when supported by the privacy threshold.</span></h2><p class="sec-note">The business processes where Cowork does the most work for the team — the clearest signal of how it's actually being used. Open the full breakdown to drill into supported aggregate detail.</p><div class="card" id="ov-proc"></div></section>
  </div>

  <div class="tab-panel" id="tab-impact">
    <section class="block"><h2 class="sec"><span class="dot"></span>Where the time went — by task category<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">The <b>method</b> used, summarized by category. Each category carries a research time band (minutes saved per run); time saved = run tasks &times; band. Category totals and reach are shown only when at least __KTHRESH__ contributors used that category. Full mapping is on the <b>How to read</b> tab.</span></h2><p class="sec-note">Understand how much time is saved by the team across supported task categories. Refer to the <button type="button" class="xref" data-goto="method" data-scroll="sec-bands"><i>How to read</i></button> section to understand the research-based time ranges.</p><p class="sec-note" style="margin-top:8px">A category appears only when at least <b>__KTHRESH__</b> contributors support it. Smaller categories are omitted instead of exposing a low-count pool.</p><div class="card" id="im-categories"></div></section>
    <section class="block"><div class="grid2">
      <div class="card"><h3>Roles Cowork stood in for</h3><p class="hint">Roles a services firm would have billed — expand for the specific skills behind them.</p><div id="im-roles"></div></div>
      <div class="card"><h3>Outputs produced — by format</h3><p class="hint">Aggregate file-format counts. Formats appear only when at least __KTHRESH__ contributors support them; individual output files and names are never listed.</p><div id="im-deliv"></div></div>
    </div></section>
  </div>

  <div class="tab-panel" id="tab-work">
    <section class="block"><h2 class="sec"><span class="dot"></span>Work by business process<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">Business processes are grouped into the shared canonical set. <b>Click a row</b> to expand aggregate format and skill summaries, each supported by at least __KTHRESH__ contributors. Named deliverables, individual records, and per-item dates are never shown.</span></h2><p class="sec-note">The business processes the team used Cowork for, ranked by time saved. <b>Click a supported process</b> to expand its cohort-qualified format and skill summaries.</p><p class="sec-note" style="margin-top:8px">Process and secondary detail with fewer than __KTHRESH__ contributing people are omitted.</p><div class="card" id="wk-proc"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Cowork fit — how well the work suited Cowork<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">Tasks are graded <b>High / Medium / Low</b> on how well they fit Cowork's agentic, cross-app strengths. <b>High</b> = work only Cowork can do (builds &amp; packaged skills, executed automations/connectors, many-source synthesis); <b>Low</b> = a single-app Copilot could have done it. The waterfall includes supported grade totals; expanded rows show only cohort-qualified process/category aggregates.</span></h2><p class="sec-note">A composition of supported graded tasks by Cowork fit, shown as a waterfall. Grades and expanded details appear only when at least __KTHRESH__ contributors support them.</p><div class="card" id="wk-fit"></div></section>
    <section class="block"><h2 class="sec"><span class="dot"></span>Category mix<button type="button" class="help" aria-label="About this section">?</button><span class="helppop">How supported role cohorts split their time across categories. A role and each category segment appear only when at least <b>__KTHRESH__</b> contributors support that breakdown. Small residual role groups are combined only if the pool also meets the threshold.</span></h2><p class="sec-note">How saved time splits across supported task categories — grouped by Role where privacy allows.</p><div class="card" id="wk-stack"></div></section>
  </div>

  <div class="tab-panel" id="tab-method">
    <details class="meth" open><summary>Glossary of terms</summary><div class="mbody" id="gloss-body">
      <p><b>Active days</b> — Person-days with at least one Cowork task in the window.</p>
      <p><b>Anonymity</b> — The public dashboard contains only team totals and breakdowns supported by at least __KTHRESH__ distinct contributors. Small residual groups and secondary details are suppressed unless their combined cohort reaches the same threshold. Contributor records remain private in the working file.</p>
      <p><b>Business process</b> — The business need served by the work &mdash; e.g., Business Value &amp; ROI Analytics.</p>
      <p><b>Contributors</b> — The number of teammates who posted their de-identified stats this period. Never named.</p>
      <p><b>Cowork fit</b> — How well a task suited Cowork's agentic, cross-app strengths, graded High / Medium / Low. High = work only Cowork can do (builds &amp; packaged skills, executed automations, many-source synthesis); Low = a single-app Copilot could have done it. Shown as a quantified waterfall on the <i>How Cowork is used</i> tab.</p>
      <p><b>Deliverables</b> — The count of <i>distinct</i> pieces of work produced.</p>
      <p><b>Hands-on time</b> — The actual time the team spent working with Cowork.</p>
      <p><b>Outputs</b> — The number of output files in a supported file-format cohort. Individual files and versions are never listed.</p>
      <p><b>Reach</b> — The number of contributors using a task category. Reach and category totals appear only when at least __KTHRESH__ contributors share it.</p>
      <p><b>Research time band</b> — The low / typical / high minutes of manual time saved per run for a task category, drawn from published studies (see &ldquo;<button type="button" class="xref" data-goto="method" data-scroll="sec-bands">Research bands &amp; sources</button>&rdquo; below).</p>
      <p><b>Run tasks</b> — A single unit of work run with Cowork — one discrete request or action (e.g., analyzing a file, drafting a document). Run tasks are grouped into sessions.</p>
      <p><b>Sessions</b> — Distinct Cowork chats run across the team. A session may contain one or multiple run tasks.</p>
      <p><b>Skills</b> — The specific capabilities behind roles (e.g., Data Visualization, Python).</p>
      <p><b>Task category</b> — How the work was done (the method) &mdash; e.g., Analysis &amp; Research, Write or debug code. Each carries a research time band (see &ldquo;<button type="button" class="xref" data-goto="method" data-scroll="sec-bands">Research bands &amp; sources</button>&rdquo; below).</p>
      <p><b>Team speed multiplier</b> — How much faster the work went: estimated hours without Cowork &divide; actual hands-on with Cowork hours.</p>
      <p><b>Time saved</b> — Manual hours Cowork saved this period: for each task, run tasks &times; the research time band for its category. The headline is the typical estimate, with a low&ndash;high range alongside.</p>
      <p><b>Recapture rate</b> — The share of time saved the team can realistically harvest into productive output. Set in the control bar (default __RECAP__%). It scales every value figure but leaves time-saved hours and counts unchanged.</p>
      <p><b>Effective time recaptured</b> — Time saved &times; the recapture rate — the productive hours the team actually reclaims. This is what the value figure prices.</p>
      <p><b>Value / cost reduction</b> — Effective time recaptured priced out: time saved &times; recapture rate &times; the hourly rate in the control bar. Recomputes whenever you change the rate or the recapture rate.</p>
    </div></details>


    <details class="meth"><summary>How task categories are derived</summary><div class="mbody">
      <p>Each task is sorted into up to two categories from three signals:</p>
      <p style="margin-bottom:3px"><b>1 · Output file type</b></p>
      <ul>
        <li>spreadsheets (.xlsx / .csv / .json) &rarr; Analysis &amp; Research</li>
        <li>code &amp; web (.py / .html / .sql / .js) &rarr; Write or debug code</li>
        <li>documents (.docx / .pdf / .pptx / images) &rarr; Document &amp; content creation</li>
        <li>packaged skills (.zip / .skill) &rarr; Specialized workflows</li>
      </ul>
      <p style="margin-bottom:3px"><b>2 · Goal keywords</b></p>
      <ul>
        <li>&ldquo;analyze / research / ROI / benchmark&rdquo; &rarr; Analysis</li>
        <li>&ldquo;debug / refactor / script / API / automation&rdquo; &rarr; Write or debug code</li>
        <li>&ldquo;email / inbox / reply&rdquo; &rarr; Email</li>
        <li>&ldquo;meeting / transcript / standup / agenda&rdquo; &rarr; Meeting</li>
      </ul>
      <p style="margin-bottom:3px"><b>3 · Input signal</b></p>
      <ul>
        <li>if the sources are data files, or there are 3 or more of them &rarr; Analysis</li>
      </ul>
      <p>A task with no saved file and no signal falls to General assistance / Other. When more than one matches, they rank (code &rsaquo; analysis &rsaquo; specialized &rsaquo; document &rsaquo; communication &rsaquo; meeting &rsaquo; email &rsaquo; general) and the top two are kept.</p>
    </div></details>


    <details class="meth"><summary>Privacy &amp; anonymity</summary><div class="mbody">
      <p><b>No contributor-level records or links are published.</b> The dashboard is built from a separate aggregate-only data payload; the private working file is not a deliverable. Categories, processes, roles, skills, formats, fit grades, and secondary details appear only when <b>__KTHRESH__+</b> distinct contributors support them. Small residual role groups and sparse detail are suppressed. Names, country, raw filenames, prompts, deliverable names, individual task rows, and per-item dates are never embedded.</p>
    </div></details>

    <details class="meth"><summary>Value model</summary><div class="mbody">
      <ul>
        <li><b>Time saved</b> = Count of run tasks × the research band (minutes saved/run).</li>
        <li><b>Recapture rate</b> = the share of time saved the team realistically converts into productive output (default __RECAP__%; adjustable in the control bar).</li>
        <li><b>Effective time recaptured</b> = time saved × recapture rate.</li>
        <li><b>Value / cost reduction</b> = effective recaptured hours × hourly rate (default $__RATE__/hr) = time saved × recapture rate × rate.</li>
        <li><b>Speed multiplier</b> = manual hours ÷ modeled hands-on hours.</li>
      </ul>
      <p>All figures come from the posts; the dashboard only re-totals and re-prices them.</p>
    </div></details>

    <details class="meth" id="sec-bands"><summary>Research bands &amp; sources</summary><div class="mbody">
      <p>Each task category carries a research-anchored time band — the minutes of manual time saved per run, at a low / typical / high estimate.<sup>†</sup> Time saved = run tasks &times; the band for that category.</p>
      <table class="dt" style="margin-top:11px">
        <thead><tr><th>Task category</th><th class="r">Low</th><th class="r">Typical</th><th class="r">High</th></tr></thead>
        <tbody>
          <tr><td><span class="catsw" style="background:var(--c0)"></span>Analysis &amp; Research</td><td class="r">30</td><td class="r">67</td><td class="r">92</td></tr>
          <tr><td><span class="catsw" style="background:var(--c1)"></span>Write or debug code</td><td class="r">30</td><td class="r">56</td><td class="r">96</td></tr>
          <tr><td><span class="catsw" style="background:var(--c2)"></span>Document &amp; content creation</td><td class="r">12</td><td class="r">24</td><td class="r">42</td></tr>
          <tr><td><span class="catsw" style="background:var(--c3)"></span>Meeting workflows</td><td class="r">12</td><td class="r">31</td><td class="r">43</td></tr>
          <tr><td><span class="catsw" style="background:var(--c5)"></span>Email workflows</td><td class="r">3</td><td class="r">7</td><td class="r">12</td></tr>
          <tr><td><span class="catsw" style="background:var(--c7)"></span>Communication workflows</td><td class="r">2</td><td class="r">4</td><td class="r">6</td></tr>
          <tr><td><span class="catsw" style="background:var(--c4)"></span>Specialized workflows</td><td class="r">10</td><td class="r">25</td><td class="r">40</td></tr>
          <tr><td><span class="catsw" style="background:var(--c6)"></span>General assistance / Other</td><td class="r">2</td><td class="r">5</td><td class="r">8</td></tr>
        </tbody>
      </table>
      <p class="footnote"><sup>†</sup> Minutes of manual time saved per run (low / typical / high). <b>Sources:</b> Stanford-WB (SSRN 5136877), Microsoft Research 2026 (DiD n=72,186), Noy &amp; Zhang (Science 2023), Cambon et al. (MSR 2024), Cui et al. (CACM 2024), Brynjolfsson, Li &amp; Raymond (QJE 2025), Forrester TEI 2024.</p>
    </div></details>
  </div>

  <footer class="foot">Generated by Microsoft Copilot Cowork · Cowork Team Report Team Dashboard skill · anonymized &amp; team-safe — numbers only, no names. Modeled estimates of tool-assisted time savings, not audited financials or performance metrics.</footer>
</div>
<script type="application/json" id="cw-data">__DATA__</script>
<script type="application/json" id="cw-glossary">__GLOSSARY__</script>
<script>__JS__</script>
</body>
</html>
"""

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
    with open(a.inp, encoding="utf-8") as handle:
        data = json.load(handle)
    public = public_data(data)
    glossary = extract_glossary(TEMPLATE)
    glossary_replacements = {
        "__RECAP__": str(int(round(public["meta"]["defaultRecapture"] * 100))),
        "__RATE__": str(public["meta"]["defaultRate"]),
        "__KTHRESH__": str(public["meta"]["kThreshold"]),
    }
    glossary = {
        term: re.sub(
            r"__[A-Z][A-Z0-9_]*__",
            lambda match: glossary_replacements.get(match.group(), match.group()),
            definition,
        )
        for term, definition in glossary.items()
    }
    replacements = {
        "__CSS__": CSS, "__JS__": JS, "__GLOSSARY__": json_for_html(glossary),
        "__DATA__": json_for_html(public),
        "__TEAM__": escape_html(public["meta"]["team"]),
        "__GENERATED__": escape_html(public["meta"]["generated"]),
        "__RATE__": escape_html(public["meta"]["defaultRate"]),
        "__RECAP__": escape_html(int(round(public["meta"]["defaultRecapture"] * 100))),
        "__KTHRESH__": escape_html(public["meta"]["kThreshold"]),
    }
    html = re.sub(r"__[A-Z][A-Z0-9_]*__", lambda match: replacements[match.group()], TEMPLATE)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build_dashboard] wrote {a.out} ({len(html)} bytes)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--out", default="output/cowork-team-roi-dashboard.html")
    main(ap.parse_args())

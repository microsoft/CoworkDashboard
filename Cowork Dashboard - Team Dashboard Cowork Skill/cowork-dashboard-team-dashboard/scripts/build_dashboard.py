#!/usr/bin/env python3
"""
build_dashboard.py — render private team_data.json into a local, aggregate-only site.

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
Usage: python build_dashboard.py --in working/team_data.json --out output/team-dashboard/index.html
"""
import json, argparse, os, re
from pathlib import Path
import tempfile


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
    """Encode public JSON defensively, including when exported outside the site."""
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def escape_html(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))
def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def summary_markdown(public):
    latest = public["snapshots"][-1]
    aggregate = public["aggregates"][latest["id"]]
    head = aggregate["head"]
    hours = head["timeTyp"]
    meta = public["meta"]
    # Team names are intentionally omitted from the shareable export.
    return (
        "# Cowork team report\n\n"
        f"Period: {latest['label']} ({latest['periodStart'] or 'unknown'}"
        f" to {latest['periodEnd'] or 'unknown'})\n\n"
        f"- Contributors: {aggregate['contributors']}\n"
        f"- Modeled time saved: {hours:.1f} hours\n"
        f"- Effective time recaptured: {hours * meta['defaultRecapture']:.1f} hours\n"
        f"- Modeled value: ${head['expertH'] * meta['defaultRecapture'] * meta['defaultRate']:,.0f}\n"
        f"- Sessions: {head['sessions']}\n"
        f"- Deliverables: {head['deliverables']}\n\n"
        "Directional tool-impact estimates, not audited financials or performance scores.\n"
        "Review this export before sharing. It contains team totals only.\n"
    )


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
    if not public["snapshots"]:
        raise ValueError("No reporting periods are available; cannot build the local dashboard.")
    assets = Path(__file__).resolve().parent.parent / "assets"
    template = (assets / "dashboard.html").read_text(encoding="utf-8")
    glossary = extract_glossary(template)
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
        "__TEAM__": escape_html(public["meta"]["team"]),
        "__GENERATED__": escape_html(public["meta"]["generated"]),
        "__RATE__": escape_html(public["meta"]["defaultRate"]),
        "__RECAP__": escape_html(int(round(public["meta"]["defaultRecapture"] * 100))),
        "__KTHRESH__": escape_html(public["meta"]["kThreshold"]),
    }
    html = re.sub(r"__[A-Z][A-Z0-9_]*__", lambda match: replacements[match.group()], template)
    output = Path(a.out)
    atomic_write(output.parent / "assets/dashboard.css",
                 (assets / "dashboard.css").read_text(encoding="utf-8"))
    atomic_write(output.parent / "assets/dashboard.js",
                 (assets / "dashboard.js").read_text(encoding="utf-8"))
    atomic_write(output.parent / "dashboard-data.json", json_for_html(public))
    atomic_write(output.parent / "dashboard-glossary.json", json_for_html(glossary))
    atomic_write(output.parent / "team-summary.md", summary_markdown(public))
    atomic_write(output, html)
    print(f"[build_dashboard] wrote local site at {output.parent}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/team_data.json")
    ap.add_argument("--out", default="output/team-dashboard/index.html")
    main(ap.parse_args())

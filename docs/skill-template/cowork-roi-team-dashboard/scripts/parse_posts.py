#!/usr/bin/env python3
"""
parse_posts.py — read the de-identified Cowork ROI posts colleagues published to the
team channel and turn them into ONE aggregated, anonymized team_data.json that
build_dashboard.py renders.

INPUT  (--in): a JSON array of channel messages. Two shapes are accepted:
  A) simplified : [{"from_id": "...", "created": "ISO8601", "subject": "...", "body": "<html>"}]
  B) Graph/MCP  : [{"from":{"user":{"id":"..."}}, "createdDateTime":"...", "body":{"content":"<html>"}}]
     (or an object with a top-level "value": [ ...Graph messages... ]).
  `from_id` is used ONLY to keep the latest post per sender and is then HASHED away —
  it is never written to the output or shown. No display names are ever read.

OUTPUT (--out): team_data.json — meta + snapshots + members[], where each member is
  {anon, role|null, posted, reports:{<snapshot>:{...metrics...}}}. NO names, NO country,
  NO file names. Role (job title) is the only attribute, and only if a post carried a
  "Role:" header line.

PARSING: stdlib only (html.parser). Tables are matched by their FIRST HEADER CELL, so
metric/section wording can drift (e.g. "Time saved" vs "Expert-equivalent hours") without
breaking. Business-process labels are collapsed via the mirrored process_groups.json and
skills are canonicalized via skills_vocabulary.json + skill_aliases.json.

Usage:
  python parse_posts.py --in working/raw_messages.json --config config/team_config.json \
                        --out working/team_data.json [--generated YYYY-MM-DD]
"""
import json, argparse, re, html, os, hashlib, collections
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))

CATEGORY_BANDS = {
    "Analysis & Research": "30 / 67 / 92", "Write or debug code": "30 / 56 / 96",
    "Document & content creation": "12 / 24 / 42", "Meeting workflows": "12 / 31 / 43",
    "Email workflows": "3 / 7 / 12", "Communication workflows": "2 / 4 / 6",
    "Specialized workflows": "10 / 25 / 40", "General assistance / Other": "2 / 5 / 8",
}

# ---------------------------------------------------------------- taxonomy load
def _load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)

def load_taxonomies():
    pg = _load("process_groups.json")
    vocab_j = _load("skills_vocabulary.json")
    vocab = {s["name"] for s in vocab_j.get("domain_skills", [])} | {s["name"] for s in vocab_j.get("tech_skills", [])}
    aliases = _load("skill_aliases.json").get("aliases", {})
    return pg, vocab, aliases

def group_process(label, pg):
    """Mirror of classify.py's grouping: groups[] passthrough -> apqc map -> keyword rules -> default."""
    if not label:
        return label
    groups = set(pg.get("groups", []))
    if label in groups:
        return label
    a2g = pg.get("apqc_to_group", {})
    if label in a2g:
        return a2g[label]
    low = label.lower()
    for rule in pg.get("keyword_rules", []):
        if any(kw.lower() in low for kw in rule.get("any", [])):
            return rule["group"]
    return pg.get("default", label)

def canon_skill(name, vocab, aliases):
    if name in vocab:
        return name
    if name in aliases:
        return aliases[name]
    return name  # unknown -> passthrough (rare; the member skill restricts to vocab)

# ---------------------------------------------------------------- html tables
class TableGrab(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._rows, self._row, self._cell = [], None, None, None
        self._in_cell = False
    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._rows = []
        elif tag == "tr" and self._rows is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []; self._in_cell = True
    def handle_endtag(self, tag):
        if tag == "table" and self._rows is not None:
            self.tables.append(self._rows); self._rows = None
        elif tag == "tr" and self._row is not None:
            self._rows.append(self._row); self._row = None
        elif tag in ("td", "th") and self._in_cell:
            self._row.append(html.unescape("".join(self._cell)).strip()); self._in_cell = False
    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)

def detag(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or ""))

def fnum(s):
    m = re.search(r"-?\d[\d,]*\.?\d*", str(s).replace(",", ""))
    return float(m.group()) if m else 0.0

def inum(s):
    return int(round(fnum(s)))

def rng(s):
    m = re.search(r"range\s*([\d.]+)\s*[–\-]\s*([\d.]+)", s) or \
        re.search(r"([\d.]+)\s*[–\-]\s*([\d.]+)", s)
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)

# ---------------------------------------------------------------- parse one post
def parse_body(body, pg, vocab, aliases, rate):
    text = detag(body)
    role = None
    mrole = re.search(r"Role:\s*([^\n<|]+?)\s*(?:\n|$)", text)
    if mrole:
        role = mrole.group(1).strip() or None
    period = {"label": "Last 15 days", "start": None, "end": None}
    mper = re.search(r"Period:\s*([^()\n]+?)\s*\((\d{4}-\d{2}-\d{2})\s*[→>-]+\s*(\d{4}-\d{2}-\d{2})\)", text)
    if mper:
        period = {"label": mper.group(1).strip(), "start": mper.group(2), "end": mper.group(3)}

    g = TableGrab(); g.feed(body)
    rec = {"headline": {}, "categories": [], "pillars": [], "processes": [], "roles": [],
           "skills": [], "io": {"inputs": [], "outputs": [], "inputsAnalyzed": 0, "outputsProduced": 0},
           "deliverables": [], "daily": []}
    hl = {"timeTyp": 0.0, "timeLow": None, "timeHigh": None, "expertH": 0.0, "assistedH": 0.0,
          "speed": 0.0, "sessions": 0, "runTasks": 0, "deliverables": 0, "activeDays": 0}

    for tbl in g.tables:
        if not tbl or not tbl[0]:
            continue
        key = tbl[0][0].strip().lower()
        rows = tbl[1:]
        if key == "metric":                                    # Headline
            for r in rows:
                if len(r) < 2: continue
                mlow, v = r[0].strip().lower(), r[1]
                if "expert-equivalent" in mlow or "time saved" in mlow:
                    if "range" in mlow and "typical" not in mlow:
                        lo, hi = rng(v); hl["timeLow"], hl["timeHigh"] = lo, hi
                    else:
                        hl["timeTyp"] = fnum(v)
                        if "range" in v.lower():
                            lo, hi = rng(v); hl["timeLow"], hl["timeHigh"] = lo, hi
                elif "speed multiplier" in mlow:
                    hl["speed"] = fnum(v)
                elif "expert vs assisted" in mlow:
                    m = re.search(r"([\d.]+)\s*h\s*expert.*?([\d.]+)\s*h\s*assisted", v, re.I)
                    if m:
                        hl["timeTyp"] = hl["timeTyp"] or float(m.group(1)); hl["assistedH"] = float(m.group(2))
                elif "assisted" in mlow:
                    hl["assistedH"] = fnum(v)
                elif mlow == "sessions":
                    hl["sessions"] = inum(v)
                elif "run task" in mlow:
                    hl["runTasks"] = inum(v)
                elif mlow.startswith("deliverable"):
                    hl["deliverables"] = inum(v)
                elif mlow == "active days":
                    hl["activeDays"] = inum(v)
        elif key == "category":                                # Where time went
            for r in rows:
                if len(r) < 4: continue
                rec["categories"].append({"name": r[0], "tasks": inum(r[2]), "hours": fnum(r[3])})
        elif key == "pillar":                                  # Value pillars
            for r in rows:
                if len(r) < 3: continue
                rec["pillars"].append({"name": r[0], "sessions": inum(r[1]), "hours": fnum(r[2])})
        elif key == "process":                                 # Business process (GROUPED)
            for r in rows:
                if len(r) < 3: continue
                rec["processes"].append({"name": group_process(r[0], pg), "sessions": inum(r[1]), "hours": fnum(r[2])})
        elif key == "role" and len(tbl[0]) == 3:               # Roles (Role|Hours|Value)
            for r in rows:
                if len(r) < 2: continue
                rec["roles"].append({"name": r[0], "hours": fnum(r[1])})
        elif key == "skill":                                   # Skills (canonicalized)
            has_hours = any("hour" in c.lower() for c in tbl[0])
            for r in rows:
                if len(r) < 4: continue
                nm = canon_skill(r[0], vocab, aliases)
                deliv, sess = inum(r[1]), inum(r[2])
                hours = fnum(r[3]) if has_hours else fnum(r[-1]) / rate
                rec["skills"].append({"name": nm, "deliverables": deliv, "sessions": sess, "hours": round(hours, 2)})
        elif key == "measure":                                 # Analyzed -> Produced totals
            for r in rows:
                if len(r) < 2: continue
                lo = r[0].strip().lower()
                if "inputs analyzed" in lo: rec["io"]["inputsAnalyzed"] = inum(r[1])
                elif "outputs produced" in lo: rec["io"]["outputsProduced"] = inum(r[1])
        elif key == "input type":
            rec["io"]["inputs"] = [{"type": r[0], "count": inum(r[1])} for r in rows if len(r) >= 2]
        elif key == "output type":
            rec["io"]["outputs"] = [{"type": r[0], "count": inum(r[1])} for r in rows if len(r) >= 2]
        elif key == "deliverable type":                        # By-type rollup (the aggregator's source)
            for r in rows:
                if len(r) < 3: continue
                skills = [canon_skill(s.strip(), vocab, aliases) for s in (r[4].split(",") if len(r) > 4 and r[4] not in ("", "—") else []) if s.strip()]
                rec["deliverables"].append({"type": r[0], "count": inum(r[1]), "hours": fnum(r[2]), "skills": sorted(set(skills))})
        elif key == "date":                                    # Activity by day
            for r in rows:
                if len(r) < 2: continue
                rec["daily"].append({"date": r[0], "runTasks": inum(r[1])})

    # normalize: canonical merges (skills/processes may collide after mapping)
    def merge(items, keyf, addf):
        out = collections.OrderedDict()
        for it in items:
            k = keyf(it)
            if k in out: addf(out[k], it)
            else: out[k] = dict(it)
        return list(out.values())
    rec["skills"] = merge(rec["skills"], lambda x: x["name"],
                          lambda a, b: a.update({"deliverables": a["deliverables"] + b["deliverables"],
                                                 "sessions": a["sessions"] + b["sessions"],
                                                 "hours": round(a["hours"] + b["hours"], 2)}))
    rec["processes"] = merge(rec["processes"], lambda x: x["name"],
                             lambda a, b: a.update({"sessions": a["sessions"] + b["sessions"],
                                                    "hours": round(a["hours"] + b["hours"], 2)}))
    hl["expertH"] = hl["timeTyp"]
    rec["headline"] = hl
    return rec, role, period

# ---------------------------------------------------------------- driver
def normalize_messages(raw):
    msgs = raw["value"] if isinstance(raw, dict) and "value" in raw else raw
    out = []
    for m in msgs:
        if "body" in m and isinstance(m["body"], dict):     # Graph shape
            fid = (((m.get("from") or {}).get("user") or {}).get("id")) or m.get("id")
            out.append({"from_id": fid, "created": m.get("createdDateTime", ""),
                        "body": (m.get("body") or {}).get("content", ""), "deleted": bool(m.get("deletedDateTime"))})
        else:                                                # simplified shape
            out.append({"from_id": m.get("from_id") or m.get("id"), "created": m.get("created", ""),
                        "body": m.get("body", ""), "deleted": bool(m.get("deleted"))})
    return out

def main(a):
    cfg = _load(os.path.relpath(a.config, HERE)) if os.path.isabs(a.config) is False and os.path.exists(os.path.join(HERE, a.config)) else json.load(open(a.config, encoding="utf-8"))
    rate = cfg.get("hourly_rate", 72)
    pg, vocab, aliases = load_taxonomies()
    raw = json.load(open(a.inp, encoding="utf-8"))
    msgs = [m for m in normalize_messages(raw) if not m["deleted"] and "Cowork ROI" in (m["body"] or "")]

    # window: keep only posts from the last N days (the latest cycle). --window-days overrides the
    # config's message_lookback_days; anchor is --now or today (UTC). Applied BEFORE the per-sender
    # dedupe so "latest post per person" is chosen from within the window.
    win = a.window_days if a.window_days is not None else cfg.get("message_lookback_days")
    if win:
        anchor = datetime.strptime(a.now, "%Y-%m-%d").date() if a.now else datetime.now(timezone.utc).date()
        cutoff = (anchor - timedelta(days=int(win))).isoformat()
        kept = [m for m in msgs if (m["created"] or "")[:10] >= cutoff]
        print(f"[parse_posts] window: last {int(win)} days (>= {cutoff}) — kept {len(kept)} of {len(msgs)} post(s)")
        msgs = kept

    # keep LATEST post per sender
    latest = {}
    for m in msgs:
        fid = m["from_id"] or "unknown"
        if fid not in latest or m["created"] > latest[fid]["created"]:
            latest[fid] = m
    senders = sorted(latest.values(), key=lambda x: x["created"])
    if not senders:
        raise SystemExit("No Cowork ROI posts found in the input.")

    members, periods, posted_dates = [], [], []
    for i, m in enumerate(senders, 1):
        rec, role, period = parse_body(m["body"], pg, vocab, aliases, rate)
        anon = str(i)  # stable, order-of-post number; from_id is hashed away (below) and never stored
        _ = hashlib.sha256((m["from_id"] or "").encode()).hexdigest()[:8]  # dedup hash; intentionally discarded
        members.append({"anon": anon, "role": role, "posted": True, "reports": {"SNAP": rec}})
        if period["start"]: periods.append(period)
        posted_dates.append((m["created"] or "")[:10])

    starts = [p["start"] for p in periods if p["start"]]
    ends = [p["end"] for p in periods if p["end"]]
    label = collections.Counter(p["label"] for p in periods).most_common(1)[0][0] if periods else "Last 15 days"
    posted_date = max(posted_dates) if posted_dates else (a.generated or "")
    snap_id = posted_date or "snapshot-1"
    snapshot = {"id": snap_id, "label": label,
                "periodStart": min(starts) if starts else None,
                "periodEnd": max(ends) if ends else None, "postedDate": posted_date}
    for mem in members:
        mem["reports"][snap_id] = mem["reports"].pop("SNAP")

    data = {
        "meta": {
            "team": cfg.get("team_name") or "Team", "channel": cfg.get("channel_name") or "",
            "generated": a.generated or posted_date, "defaultRate": rate,
            "cadenceDays": cfg.get("cadence_days", 14), "kThreshold": cfg.get("privacy_k_threshold", 3),
            "teamSize": cfg.get("team_size"), "categoryBands": CATEGORY_BANDS,
        },
        "snapshots": [snapshot], "members": members,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    rolev = sum(1 for x in members if x["role"])
    print(f"[parse_posts] {len(members)} contributor(s) · roles present on {rolev} · "
          f"period {snapshot['periodStart']}→{snapshot['periodEnd']} · rate ${rate}/hr")
    print(f"[parse_posts] wrote {a.out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--config", default="config/team_config.json")
    ap.add_argument("--out", default="working/team_data.json")
    ap.add_argument("--generated", default=None, help="YYYY-MM-DD stamp (defaults to newest post date)")
    ap.add_argument("--window-days", dest="window_days", type=int, default=None,
                    help="Keep only posts from the last N days (defaults to config message_lookback_days)")
    ap.add_argument("--now", default=None, help="YYYY-MM-DD anchor for --window-days (defaults to today, UTC)")
    main(ap.parse_args())

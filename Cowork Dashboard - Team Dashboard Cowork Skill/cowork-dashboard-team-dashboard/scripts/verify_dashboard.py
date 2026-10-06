#!/usr/bin/env python3
"""Verify the dashboard UI and its cohort-filtered public data contract."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from html.parser import HTMLParser


EXPECTED_TABS = ["overview", "impact", "work", "method"]
REQUIRED_IDS = {
    "im-categories": "category bar chart",
    "wk-stack": "stacked category mix",
    "wk-fit": "Cowork-fit waterfall",
    "wk-proc": "business-process drill-downs",
    "snapSel": "period selector",
    "rateInput": "hourly-rate control",
    "recapInput": "recapture-rate control",
    "ovSeg": "time/value toggle",
    "resetBtn": "reset control",
    "printBtn": "print control",
}
REQUIRED_RENDER_SIGNATURES = {
    'class="wf-svg"': "waterfall SVG renderer",
    'class="stackbar"': "stacked-mix renderer",
    '<details class="acct-row"': "expandable process rows",
    'data-metric="time"': "time toggle option",
    'data-metric="value"': "value toggle option",
    "function barRow(": "category bar renderer",
    "function renderCategoryMix(": "cohort-filtered category mix",
}
FORBIDDEN_DATA_KEYS = {
    "anon", "member", "members", "reports", "role", "displayname",
    "userprincipalname", "mail", "email", "sender", "userid", "user_id",
    "country", "filename", "file_name", "prompt", "deliverablesdetail",
    "daily", "coworkfit",
}
AGGREGATE_KEYS = {
    "contributors", "head", "categories", "processes", "roles", "skills",
    "deliverables", "processDetails", "fit", "fitDetails", "roleGroups",
    "inputs", "outputs", "kThreshold",
}


SITE_FILES = {
    "assets/dashboard.css", "assets/dashboard.js",
    "dashboard-data.json", "dashboard-glossary.json", "team-summary.md",
}


class SiteMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.stylesheets = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if any(key.lower().startswith("on") for key in attributes):
            self.errors.append("inline event handler in local site")
        if tag == "script":
            self.scripts.append(attributes.get("src"))
        if tag == "style":
            self.errors.append("inline stylesheet in local site")
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.stylesheets.append(attributes.get("href"))


def find_forbidden_keys(value, path="$"):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_DATA_KEYS:
                found.append(child_path)
            found.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def verify_public_contract(data):
    errors = []
    if set(data) != {"meta", "snapshots", "aggregates"}:
        errors.append("public data must contain only meta, snapshots, and aggregates")
        return errors

    threshold = data.get("meta", {}).get("kThreshold")
    if not isinstance(threshold, int) or threshold < 2:
        errors.append("public data has no valid minimum cohort threshold")
        return errors

    snapshots = data.get("snapshots")
    aggregates = data.get("aggregates")
    if not isinstance(snapshots, list) or not isinstance(aggregates, dict):
        errors.append("public snapshots or aggregate index has the wrong shape")
        return errors
    expected_ids = {str(snapshot.get("id", "")) for snapshot in snapshots}
    if not expected_ids.issubset(aggregates) or "ALL" not in aggregates:
        errors.append("public aggregate index is missing a reporting period")

    for aggregate_id, aggregate in aggregates.items():
        if not isinstance(aggregate, dict) or set(aggregate) != AGGREGATE_KEYS:
            errors.append(f"aggregate {aggregate_id!r} has an unexpected data shape")
            continue
        for key in ("categories", "processes", "roles", "skills", "deliverables",
                    "processDetails", "fit", "fitDetails", "roleGroups", "inputs", "outputs"):
            if not isinstance(aggregate.get(key), list):
                errors.append(f"aggregate {aggregate_id!r} has invalid {key} data")
        for key in ("categories", "processes", "roles", "skills", "deliverables",
                    "fit", "inputs", "outputs"):
            for item in aggregate.get(key, []):
                if not isinstance(item.get("contributors"), int) or item["contributors"] < threshold:
                    errors.append(f"aggregate {aggregate_id!r} exposes {key} below the cohort threshold")
        for key in ("processDetails", "fitDetails"):
            for item in aggregate.get(key, []):
                if not isinstance(item.get("contributors"), int) or item["contributors"] < threshold:
                    errors.append(f"aggregate {aggregate_id!r} exposes {key} below the cohort threshold")
                for skill in item.get("skills", []):
                    if not isinstance(skill.get("contributors"), int) or skill["contributors"] < threshold:
                        errors.append(f"aggregate {aggregate_id!r} exposes a detail skill below the cohort threshold")
        for group in aggregate.get("roleGroups", []):
            if not isinstance(group.get("contributors"), int) or group["contributors"] < threshold:
                errors.append(f"aggregate {aggregate_id!r} exposes a role pool below the cohort threshold")
            for category in group.get("categories", []):
                if not isinstance(category.get("contributors"), int) or category["contributors"] < threshold:
                    errors.append(f"aggregate {aggregate_id!r} exposes a role/category below the cohort threshold")

    return errors


def verify_layout(html):
    errors = []
    tabs = re.findall(r'class="tab-btn(?: on)?"[^>]*data-tab="([^"]+)"', html)
    if tabs != EXPECTED_TABS:
        errors.append(f"expected four tabs {EXPECTED_TABS}, found {tabs or 'none'}")
    panels = re.findall(r'class="tab-panel(?: on)?" id="tab-([^"]+)"', html)
    if panels != EXPECTED_TABS:
        errors.append(f"expected four matching tab panels {EXPECTED_TABS}, found {panels or 'none'}")

    for element_id, label in REQUIRED_IDS.items():
        if not re.search(rf'\bid="{re.escape(element_id)}"', html):
            errors.append(f"missing required {label} (#{element_id})")
    return errors


class AttachmentMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = {}
        self.current = None
        self.errors = []
        self.styles = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if any(key.lower().startswith("on") for key in attributes):
            self.errors.append("inline event handler in report attachment")
        if tag == "script":
            if "src" in attributes:
                self.errors.append("external script in report attachment")
            key = attributes.get("id", "runtime")
            if key in self.scripts:
                self.errors.append("duplicate embedded script: " + key)
            self.current = key
            self.scripts[key] = ""
        if tag == "style":
            self.styles += 1
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.errors.append("external stylesheet in report attachment")

    def handle_data(self, data):
        if self.current is not None:
            self.scripts[self.current] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None


def verify_attachment(path):
    if not os.path.isfile(path):
        return [f"report attachment does not exist: {path}"]
    html = Path(path).read_text(encoding="utf-8")
    errors = verify_layout(html)
    markup = AttachmentMarkup()
    markup.feed(html)
    errors.extend(markup.errors)
    if markup.styles != 1 or set(markup.scripts) != {"runtime", "report-data", "report-glossary"}:
        errors.append("report must contain embedded styling, runtime, aggregate data and glossary")
        return errors
    runtime = markup.scripts["runtime"]
    if "fetch(" in runtime or 'href="team-summary.md"' in html:
        errors.append("report attachment requires a companion file or network fetch")
    for signature, label in REQUIRED_RENDER_SIGNATURES.items():
        if signature not in html and signature not in runtime:
            errors.append(f"missing required {label}")
    if re.search(r"__[A-Z][A-Z0-9_]*__", html):
        errors.append("unresolved report placeholders")
    try:
        data = json.loads(markup.scripts["report-data"])
        glossary = json.loads(markup.scripts["report-glossary"])
        if not isinstance(glossary, dict):
            errors.append("embedded glossary has the wrong shape")
        errors.extend(verify_public_contract(data))
        if find_forbidden_keys(data):
            errors.append("identifying fields remain in embedded public data")
    except (ValueError, TypeError) as exc:
        errors.append(f"invalid embedded report data: {exc}")
    return errors


def verify(path):
    if not os.path.isfile(path):
        return [f"dashboard file does not exist: {path}"]
    html = Path(path).read_text(encoding="utf-8")
    if 'id="report-data"' in html:
        return verify_attachment(path)
    errors = verify_layout(html)
    markup = SiteMarkup()
    markup.feed(html)
    errors.extend(markup.errors)
    if markup.scripts != ["assets/dashboard.js"]:
        errors.append("site must load exactly one local runtime, with no inline scripts")
    if markup.stylesheets != ["assets/dashboard.css"]:
        errors.append("site must load the local stylesheet")
    root = Path(path).resolve().parent
    for relative in SITE_FILES:
        asset = root / relative
        if not asset.is_file() or not asset.resolve().is_relative_to(root):
            errors.append(f"missing or unconfined local-site asset: {relative}")
    if errors:
        return errors
    runtime = (root / "assets/dashboard.js").read_text(encoding="utf-8")
    for signature, label in REQUIRED_RENDER_SIGNATURES.items():
        if signature not in html and signature not in runtime:
            errors.append(f"missing required {label}")

    placeholders = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", html)))
    if placeholders:
        errors.append("unresolved template placeholders: " + ", ".join(placeholders))

    try:
        data = json.loads((root / "dashboard-data.json").read_text(encoding="utf-8"))
        glossary = json.loads((root / "dashboard-glossary.json").read_text(encoding="utf-8"))
        if not isinstance(glossary, dict):
            raise ValueError("local glossary has the wrong shape")
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    else:
        forbidden = find_forbidden_keys(data)
        if forbidden:
            errors.append("contributor-level or identifying fields remain in public data: "
                          + ", ".join(forbidden))
        errors.extend(verify_public_contract(data))

    return errors


def main(args):
    errors = verify(args.inp)
    if errors:
        print("[verify_dashboard] FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        "[verify_dashboard] passed: dashboard assets, tabs, charts, controls, "
        "and cohort-filtered public data"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default="output/team-dashboard/index.html")
    main(parser.parse_args())

#!/usr/bin/env python3
"""Verify that the bundled team dashboard renderer produced the required UI."""
import argparse
import json
import os
import re
import sys


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
}
FORBIDDEN_DATA_KEYS = {
    "displayname",
    "userprincipalname",
    "mail",
    "email",
    "sender",
    "userid",
    "user_id",
    "country",
    "filename",
    "file_name",
    "prompt",
}


def embedded_data(html):
    match = re.search(
        r'<script type="application/json" id="cw-data">(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        raise ValueError("embedded aggregate data block #cw-data is missing")
    return json.loads(match.group(1))


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


def reports_from(data):
    reports = []
    for member in data.get("members", []):
        member_reports = member.get("reports", {})
        if isinstance(member_reports, dict):
            reports.extend(
                report for report in member_reports.values()
                if isinstance(report, dict)
            )
    return reports


def verify(path):
    errors = []
    if not os.path.isfile(path):
        return [f"dashboard file does not exist: {path}"]

    with open(path, encoding="utf-8") as handle:
        html = handle.read()

    tabs = re.findall(r'class="tab-btn(?: on)?"[^>]*data-tab="([^"]+)"', html)
    if tabs != EXPECTED_TABS:
        errors.append(
            f"expected four tabs {EXPECTED_TABS}, found {tabs or 'none'}"
        )
    panels = re.findall(r'class="tab-panel(?: on)?" id="tab-([^"]+)"', html)
    if panels != EXPECTED_TABS:
        errors.append(
            f"expected four matching tab panels {EXPECTED_TABS}, found {panels or 'none'}"
        )

    for element_id, label in REQUIRED_IDS.items():
        if not re.search(rf'\bid="{re.escape(element_id)}"', html):
            errors.append(f"missing required {label} (#{element_id})")
    for signature, label in REQUIRED_RENDER_SIGNATURES.items():
        if signature not in html:
            errors.append(f"missing required {label}")

    placeholders = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", html)))
    if placeholders:
        errors.append("unresolved template placeholders: " + ", ".join(placeholders))

    try:
        data = embedded_data(html)
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    else:
        forbidden = find_forbidden_keys(data)
        if forbidden:
            errors.append(
                "identifying fields remain in embedded data: " + ", ".join(forbidden)
            )
        reports = reports_from(data)
        if not any(report.get("categories") for report in reports):
            errors.append(
                "category bars and stacked mix have no aggregate category inputs"
            )
        if not any(report.get("processes") for report in reports):
            errors.append(
                "business-process drill-downs have no aggregate process inputs"
            )
        if not any(report.get("coworkFit") for report in reports):
            errors.append(
                "Cowork-fit waterfall has no aggregate fit inputs"
            )

    return errors


def main(args):
    errors = verify(args.inp)
    if errors:
        print("[verify_dashboard] FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        "[verify_dashboard] passed: four tabs, required aggregate visuals, "
        "controls, and de-identified embedded data"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in",
        dest="inp",
        default="output/cowork-team-roi-dashboard.html",
    )
    main(parser.parse_args())

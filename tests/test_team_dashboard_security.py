import copy
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "Cowork Dashboard - Team Dashboard Cowork Skill" / "cowork-dashboard-team-dashboard"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_dashboard  # noqa: E402
import parse_posts  # noqa: E402
import verify_dashboard  # noqa: E402


def report(category, process, role="Software Engineer", skill="Python", fit="H"):
    return {
        "headline": {
            "timeTyp": 5, "timeLow": 3, "timeHigh": 7, "expertH": 5,
            "assistedH": 1, "sessions": 2, "runTasks": 3,
            "deliverables": 2, "activeDays": 1,
        },
        "categories": [{"name": category, "tasks": 3, "hours": 5}],
        "processes": [{"name": process, "sessions": 2, "hours": 5}],
        "roles": [{"name": role, "hours": 5}],
        "skills": [{"name": skill, "deliverables": 2, "sessions": 2, "hours": 5}],
        "deliverables": [{"type": "Web page", "count": 2, "hours": 5}],
        "deliverablesDetail": [{
            "name": "Secret contributor project name",
            "type": "Web page",
            "date": "2026-10-01",
            "process": process,
            "skills": [skill],
            "hours": 5,
        }],
        "coworkFit": [{
            "grade": fit, "process": process, "category": category, "hours": 5,
            "taskDescription": "A private contributor task",
        }],
        "io": {"inputs": [], "outputs": [], "inputsAnalyzed": 1, "outputsProduced": 2},
        "daily": [{"date": "2026-10-01", "runTasks": 3}],
    }


def private_data():
    members = []
    assignments = [
        ("Data Analyst", "Analysis & Research", "Technology & Engineering", "H"),
        ("Data Analyst", "Analysis & Research", "Technology & Engineering", "H"),
        ("Data Analyst", "Analysis & Research", "Technology & Engineering", "H"),
        ("UX Designer", "Write or debug code", "Strategy & Planning", "L"),
        ("Software Engineer", "Specialized workflows", "Sales & Customer Engagement", "L"),
    ]
    for index, (role, category, process, fit) in enumerate(assignments):
        members.append({
            "anon": str(index + 1),
            "role": role,
            "posted": True,
            "reports": {"2026-10-01": report(category, process, fit=fit)},
        })
    return {
        "meta": {
            "team": "Test team", "channel": "private channel",
            "generated": "2026-10-02", "defaultRate": 72,
            "defaultRecapture": 0.7, "kThreshold": 3,
        },
        "snapshots": [{
            "id": "2026-10-01", "label": "Last 15 days",
            "periodStart": "2026-09-16", "periodEnd": "2026-10-01",
            "postedDate": "2026-10-01",
        }],
        "members": members,
    }


class TeamDashboardSecurityTests(unittest.TestCase):
    def test_public_payload_suppresses_small_and_residual_cohorts(self):
        result = build_dashboard.public_data(private_data())
        current = result["aggregates"]["2026-10-01"]

        self.assertEqual([item["name"] for item in current["categories"]], ["Analysis & Research"])
        self.assertEqual([item["name"] for item in current["processes"]], ["Technology & Engineering"])
        self.assertEqual([item["name"] for item in current["roleGroups"]], ["Data Analyst"])
        self.assertEqual([item["name"] for item in current["roles"]], ["Software Engineer"])
        self.assertEqual([item["grade"] for item in current["fit"]], ["H"])
        self.assertTrue(all(row["contributors"] >= 3 for row in current["categories"]))
        self.assertTrue(all(row["contributors"] >= 3 for row in current["processes"]))
        self.assertTrue(all(row["contributors"] >= 3 for row in current["fit"]))
        self.assertEqual(len(current["processDetails"]), 1)
        self.assertEqual(current["processDetails"][0]["type"], "HTML")
        self.assertNotIn("Secret contributor project name", json.dumps(result))
        self.assertNotIn("taskDescription", json.dumps(result))
        self.assertNotIn("members", result)
        self.assertNotIn("reports", json.dumps(result))

    def test_realistic_parsed_posts_cannot_inject_markup_or_script_terminators(self):
        with tempfile.TemporaryDirectory(prefix="dashboard-xss-test-") as temp:
            temp = pathlib.Path(temp)
            messages = json.loads((SKILL / "examples/sample_raw_messages.json").read_text(encoding="utf-8"))
            messages[0]["body"] = messages[0]["body"].replace(
                "<td>Analysis &amp; Research</td>",
                "<td>&lt;img src=x onerror=alert(1)&gt;</td>",
                1,
            )
            raw_path = temp / "raw_messages.json"
            raw_path.write_text(json.dumps(messages), encoding="utf-8")

            config = json.loads((SKILL / "config/team_config.json").read_text(encoding="utf-8"))
            config["team_name"] = '"><img src=x onerror=alert(1)></script><script>alert(1)</script>'
            config_path = temp / "team_config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            parsed_path = temp / "team_data.json"
            html_path = temp / "dashboard.html"

            parse_posts.main(SimpleNamespace(
                inp=str(raw_path), config=str(config_path), out=str(parsed_path),
                generated="</script><script>alert(1)</script>",
                window_days=15, now="2026-07-02",
            ))
            parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
            self.assertIn(
                "<img src=x onerror=alert(1)>",
                parsed["members"][0]["reports"]["2026-07-01"]["categories"][0]["name"],
            )
            build_dashboard.main(SimpleNamespace(inp=str(parsed_path), out=str(html_path)))
            html = html_path.read_text(encoding="utf-8")

            self.assertNotIn("</script><script>alert(1)", html.lower())
            self.assertNotIn('<img src=x onerror=alert(1)>', html.lower())
            self.assertIn(r"\u003c/script\u003e", html.lower())
            self.assertEqual(verify_dashboard.verify(str(html_path)), [])

    def test_verifier_rejects_a_public_breakdown_below_threshold(self):
        data = build_dashboard.public_data(private_data())
        data = copy.deepcopy(data)
        data["aggregates"]["2026-10-01"]["categories"][0]["contributors"] = 2
        errors = verify_dashboard.verify_public_contract(data)
        self.assertTrue(any("below the cohort threshold" in error for error in errors))

    def test_context_encoders_escape_html_and_script_element_delimiters(self):
        attack = '</script><img src="x" onerror="alert(1)">&'
        encoded_json = build_dashboard.json_for_html({"text": attack})
        self.assertNotIn("<", encoded_json)
        self.assertNotIn("&", encoded_json)
        self.assertEqual(json.loads(encoded_json), {"text": attack})
        self.assertEqual(
            build_dashboard.escape_html(attack),
            "&lt;/script&gt;&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;&amp;",
        )


if __name__ == "__main__":
    unittest.main()

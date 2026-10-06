import copy
import json
import pathlib
import sys
import tempfile
import unittest
import http.client
import threading
from types import SimpleNamespace


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "Cowork Dashboard - Team Dashboard Cowork Skill" / "cowork-dashboard-team-dashboard"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_dashboard  # noqa: E402
import parse_posts  # noqa: E402
import verify_dashboard  # noqa: E402
import serve_dashboard  # noqa: E402
import build_outputs  # noqa: E402


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
            parsed_path = temp / "working/team_data.json"
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
            self.assertTrue(html_path.is_file())
            html = html_path.read_text(encoding="utf-8")
            public_json = (temp / "dashboard-data.json").read_text(encoding="utf-8")

            self.assertNotIn("</script><script>alert(1)", html.lower())
            self.assertNotIn('<img src=x onerror=alert(1)>', html.lower())
            self.assertIn(r"\u003c/script\u003e", public_json.lower())
            self.assertNotIn("<script>", html.lower())
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

    def test_local_site_has_separate_assets_and_only_public_data(self):
        with tempfile.TemporaryDirectory(prefix="dashboard-site-test-") as temp:
            root = pathlib.Path(temp)
            raw = root / "private/team_data.json"
            raw.parent.mkdir()
            raw.write_text(json.dumps(private_data()), encoding="utf-8")
            page = root / "site/index.html"
            build_dashboard.main(SimpleNamespace(inp=str(raw), out=str(page)))
            self.assertTrue(page.is_file())
            self.assertEqual(verify_dashboard.verify(str(page)), [])
            html = page.read_text(encoding="utf-8")
            self.assertIn('src="assets/dashboard.js"', html)
            self.assertIn('<a class="btn" href="team-summary.md">Open Markdown summary</a>', html)
            self.assertEqual(
                (page.parent / "assets/dashboard.js").read_bytes(),
                build_dashboard.DASHBOARD_RUNTIME.encode("utf-8"),
            )
            self.assertNotIn("<style>", html)
            self.assertNotIn('type="application/json"', html)
            public = json.loads((page.parent / "dashboard-data.json").read_text())
            self.assertEqual(verify_dashboard.verify_public_contract(public), [])
            export = (page.parent / "team-summary.md").read_text()
            self.assertIn("Modeled time saved: 25.0 hours", export)
            self.assertNotIn("Secret contributor", export)
            self.assertNotIn("private channel", export)
            (page.parent / "assets/dashboard.js").unlink()
            self.assertTrue(verify_dashboard.verify(str(page)))

    def test_installer_manifest_uses_synchronized_source_templates(self):
        template = ROOT / "docs/skill-template" / SKILL.name
        manifest = json.loads((template.parent / "manifest-dashboard.json").read_text())
        source_files = {
            path.relative_to(SKILL).as_posix()
            for path in SKILL.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(set(manifest), {SKILL.name + "/" + name for name in source_files})
        self.assertFalse((SKILL / "assets/dashboard.html").exists())
        self.assertFalse((SKILL / "assets/dashboard.js").exists())
        self.assertFalse(any(name.endswith((".html", ".js", ".template")) for name in source_files))
        self.assertNotIn("scripts/dashboard_template.py", source_files)
        self.assertIn("scripts/dashboard_runtime.py", source_files)
        for name in source_files:
            self.assertEqual((SKILL / name).read_bytes(), (template / name).read_bytes(), name)
        self.assertFalse((template / "assets/dashboard.html").exists())
        self.assertFalse((template / "assets/dashboard.js").exists())

    def test_generated_html_escapes_metadata_and_runtime_matches_previous_release(self):
        import hashlib

        meta = build_dashboard.public_data(private_data())["meta"]
        meta["team"] = '<img src=x onerror="alert(1)">'
        meta["generated"] = "</script><script>alert(1)</script>"
        html = build_dashboard.dashboard_html(meta)
        self.assertNotIn(meta["team"], html)
        self.assertNotIn(meta["generated"], html)
        self.assertIn(build_dashboard.escape_html(meta["team"]), html)
        self.assertIn(build_dashboard.escape_html(meta["generated"]), html)
        self.assertIn('id="gloss-body"', html)
        self.assertEqual(
            hashlib.sha256(build_dashboard.DASHBOARD_RUNTIME.encode("utf-8")).hexdigest(),
            "a003e5edd5595c1896389bdd1d59a1706cad03ca116c50bf5232894030be9ccc",
        )

    def test_loopback_server_blocks_commands_rebinding_traversal_and_private_files(self):
        with tempfile.TemporaryDirectory(prefix="dashboard-server-test-") as temp:
            root = pathlib.Path(temp)
            raw = root / "team_data.json"
            raw.write_text(json.dumps(private_data()), encoding="utf-8")
            site = root / "site"
            build_dashboard.main(SimpleNamespace(inp=str(raw), out=str(site / "index.html")))
            (site / "private.json").write_text('{"secret":"never serve"}')
            server = serve_dashboard.make_server(site, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(path, method="GET", headers=None):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                    try:
                        connection.request(method, path, headers=headers or {})
                        response = connection.getresponse()
                        return response.status, dict(response.getheaders()), response.read()
                    finally:
                        connection.close()

                status, headers, body = request("/")
                self.assertEqual(status, 200)
                self.assertIn(b"Cowork Team Dashboard", body)
                self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(request("/health")[0], 200)
                self.assertEqual(request("/assets/dashboard.js")[0], 200)
                self.assertEqual(request("/dashboard-data.json")[0], 200)
                self.assertEqual(request("/run/impact")[0], 405)
                self.assertEqual(request("/run/impact", "POST")[0], 405)
                self.assertEqual(request("/", headers={"Host": "evil.test"})[0], 421)
                self.assertEqual(request("/", headers={"Origin": "https://evil.test"})[0], 403)
                self.assertEqual(request("/..%2fteam_data.json")[0], 400)
                self.assertEqual(request("/assets%5c..%5cteam_data.json")[0], 400)
                self.assertEqual(request("/private.json")[0], 404)
                self.assertEqual(request("/team_data.json")[0], 404)
                (site / "dashboard-data.json").unlink()
                (site / "dashboard-data.json").symlink_to(raw)
                self.assertEqual(request("/dashboard-data.json")[0], 400)
                self.assertEqual(request("/health", "HEAD")[2], b"")
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_build_rejects_overlapping_runs_and_releases_lock_on_failure(self):
        with tempfile.TemporaryDirectory(prefix="dashboard-lock-test-") as temp:
            root = pathlib.Path(temp)
            page = root / "index.html"
            lock = root / ".dashboard-build.lock"
            lock.mkdir()
            args = SimpleNamespace(inp=str(root / "missing.json"), out_html=str(page))
            with self.assertRaisesRegex(SystemExit, "another build is active"):
                build_outputs.main(args)
            self.assertTrue(lock.is_dir())
            lock.rmdir()
            with self.assertRaises(FileNotFoundError):
                build_outputs.main(args)
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()

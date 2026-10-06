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
    def test_sparse_process_outputs_group_by_type_and_keep_skills_private(self):
        data = private_data()
        detail = data["members"][-1]["reports"]["2026-10-01"]["deliverablesDetail"]
        detail.append(dict(detail[0], type="HTML", hours=2))
        detail.append(dict(detail[0], type="PPTX", hours=1))
        public = build_dashboard.public_data(data)
        for aggregate in public["aggregates"].values():
            rows = [row for row in aggregate["processDetails"]
                    if row["process"] == "Sales & Customer Engagement"]
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["type"]: (row["count"], row["hours"]) for row in rows},
                             {"HTML": (2, 7), "PPTX": (1, 1)})
            self.assertTrue(all(row["contributors"] is None for row in rows))
            self.assertTrue(all(row["skills"] == [] for row in rows))
        self.assertEqual(verify_dashboard.verify_public_contract(public), [])
        self.assertNotIn("Secret contributor project name", json.dumps(public))
        public["aggregates"]["2026-10-01"]["processDetails"][-1]["skills"] = [
            {"name": "Python", "count": 1, "contributors": 1}
        ]
        self.assertTrue(verify_dashboard.verify_public_contract(public))

    def test_overview_process_ranking_has_dynamic_count_and_breakdown_link(self):
        runtime = build_dashboard.dashboard_runtime()
        self.assertIn("const PROCESS_ICON=", runtime)
        self.assertIn('class="proc-icon" aria-hidden="true"', runtime)
        self.assertIn("const topProcesses=processes.slice(0,5);", runtime)
        self.assertIn("Top ${topProcesses.length} of ${processes.length} business processes", runtime)
        self.assertIn('class="xref" data-goto="work" data-scroll="wk-proc">open the full breakdown', runtime)
        self.assertIn("${pct(item.hours,totalProcessHours)}% of total", runtime)
        self.assertIn("Open the full breakdown to drill into each one.", build_dashboard.dashboard_markup())

    def test_all_fit_grades_and_details_survive_below_threshold(self):
        data = private_data()
        data["members"][0]["reports"]["2026-10-01"]["coworkFit"][0]["grade"] = "M"
        public = build_dashboard.public_data(data)
        for aggregate in public["aggregates"].values():
            self.assertEqual({row["grade"] for row in aggregate["fit"]}, {"H", "M", "L"})
            self.assertTrue(all(row["contributors"] is None for row in aggregate["fit"]))
            self.assertTrue(all(row["contributors"] is None for row in aggregate["fitDetails"]))
            self.assertEqual(sum(row["count"] for row in aggregate["fit"]), 5)
            self.assertEqual(sum(row["count"] for row in aggregate["fitDetails"]), 5)
            self.assertEqual(sum(row["hours"] for row in aggregate["fit"]), 25)
            self.assertEqual(len(aggregate["processDetails"]), 3)
        self.assertEqual(verify_dashboard.verify_public_contract(public), [])
        runtime = build_dashboard.dashboard_runtime()
        self.assertIn("Total graded tasks", runtime)
        self.assertNotIn("graded tasks in supported cohorts", runtime)

    def test_process_empty_state_uses_requested_message(self):
        runtime = build_dashboard.dashboard_runtime()
        self.assertIn(
            "No per-item detail for this process in the current posts. "
            "Deliverable names are de-identified by the Member skill (no file names); "
            "the list appears here when a teammate&#39;s post carries it.",
            runtime,
        )
        self.assertNotIn("No process detail met the minimum contributor threshold.", runtime)

    def test_all_service_roles_skills_and_output_formats_include_sparse_totals(self):
        data = private_data()
        sparse = data["members"][-1]["reports"]["2026-10-01"]
        sparse["roles"] = [{"name": "Technical Writer", "hours": 5}]
        sparse["skills"] = [{"name": "Data Visualization", "deliverables": 2, "sessions": 2, "hours": 5}]
        sparse["deliverables"] = [{"type": "CSV", "count": 2, "hours": 5}]
        public = build_dashboard.public_data(data)
        for current in public["aggregates"].values():
            for key, name, field, total in (
                ("roles", "Technical Writer", "hours", 25),
                ("skills", "Data Visualization", "hours", 25),
                ("deliverables", "Excel / CSV", "count", 10),
            ):
                rows = current[key]
                self.assertIsNone(next(row["contributors"] for row in rows if row["name"] == name))
                self.assertEqual(sum(row[field] for row in rows), total)
            self.assertEqual([row["name"] for row in current["roleGroups"]], ["Data Analyst"])
            self.assertEqual(len(current["processDetails"]), 3)
        self.assertEqual(verify_dashboard.verify_public_contract(public), [])
        runtime = build_dashboard.dashboard_runtime()
        self.assertNotIn("serviceRoles.slice", runtime)
        self.assertIn("All reported skills", runtime)
        self.assertNotIn("Formats with fewer than", runtime)

    def test_approved_exceptions_never_publish_exact_small_reach(self):
        for key in ("categories", "processes", "roles", "skills", "deliverables", "fit", "fitDetails", "processDetails"):
            for reach in (1, 2, True):
                with self.subTest(key=key, reach=reach):
                    public = build_dashboard.public_data(private_data())
                    public["aggregates"]["2026-10-01"][key][0]["contributors"] = reach
                    self.assertTrue(verify_dashboard.verify_public_contract(public))

    def test_email_body_uses_headline_tasks_not_filtered_category_subtotal(self):
        public = build_dashboard.public_data(private_data())
        body = build_dashboard.summary_email(public)
        self.assertIn("Team Cowork rollup", body)
        self.assertIn("15 run tasks", body)
        self.assertNotIn("9 run tasks", body)
        self.assertIn("$1,260 modeled recapture value", body)
        self.assertIn("Technology &amp; Engineering", body)
        self.assertIn("Strategy &amp; Planning", body)
        self.assertNotIn("Secret contributor", body)
        self.assertNotIn("Sales &amp; Customer Engagement", body)

    def test_member_moderate_fit_tasks_are_counted_as_medium(self):
        pg, vocab, aliases = parse_posts.load_taxonomies()
        body = """<table><tr><th>Fit</th><th>Business process</th><th>Method</th><th>Hours</th></tr>
<tr><td>High fit</td><td>Technology &amp; Engineering</td><td>Analysis &amp; Research</td><td>5</td></tr>
<tr><td>Moderate fit</td><td>Technology &amp; Engineering</td><td>Analysis &amp; Research</td><td>3</td></tr>
<tr><td>Medium fit</td><td>Technology &amp; Engineering</td><td>Analysis &amp; Research</td><td>2</td></tr>
<tr><td>Low fit</td><td>Technology &amp; Engineering</td><td>Analysis &amp; Research</td><td>1</td></tr></table>"""
        parsed, _role, _period = parse_posts.parse_body(body, pg, vocab, aliases, 72)
        self.assertEqual([item["grade"] for item in parsed["coworkFit"]], ["H", "M", "M", "L"])
        data = private_data()
        for member in data["members"]:
            member["reports"]["2026-10-01"]["coworkFit"] = parsed["coworkFit"]
            member["reports"]["2026-10-01"]["headline"]["runTasks"] = 4
            member["reports"]["2026-10-01"]["categories"] = [
                {"name": "Analysis & Research", "tasks": 4, "hours": 11}
            ]
        aggregate = build_dashboard.public_data(data)["aggregates"]["2026-10-01"]
        self.assertEqual(aggregate["head"]["runTasks"], 20)
        self.assertEqual(sum(item["tasks"] for item in aggregate["categories"]), 20)
        self.assertEqual(sum(item["count"] for item in aggregate["fit"]), 20)

    def test_incomplete_email_links_are_detected_and_complete_reports_are_not(self):
        samples = json.loads((SKILL / "examples/sample_raw_messages.json").read_text())
        full = samples[0]["body"]
        url = "https://outlook.office.com/mail/deeplink/read/report-123"
        stub = '<p>Cowork Team Report</p><a href="' + url + '">View original email</a>'
        raw = {"value": [
            {"id": "post-1", "createdDateTime": "2026-07-01T10:00:00Z",
             "from": {"user": {"id": "sender-1"}}, "body": {"content": stub}},
            {"id": "post-2", "createdDateTime": "2026-07-01T11:00:00Z",
             "body": {"content": full + '<a href="' + url + '">Email</a>'}},
            {"id": "old", "createdDateTime": "2026-01-01", "body": {"content": stub}},
            {"id": "deleted", "createdDateTime": "2026-07-01",
             "deletedDateTime": "2026-07-02", "body": {"content": stub}},
        ]}
        requests = parse_posts.linked_email_requests(raw, 15, "2026-07-02")
        self.assertEqual([item["message_index"] for item in requests], [0])
        self.assertEqual(requests[0]["email_links"], [url])
        original = parse_posts.normalize_messages(raw)[0]
        raw["value"][0]["body"]["content"] = full
        recovered = parse_posts.normalize_messages(raw)[0]
        self.assertEqual(original["from_id"], recovered["from_id"])
        self.assertEqual(original["created"], recovered["created"])
        self.assertEqual(parse_posts.linked_email_requests(raw, 15, "2026-07-02"), [])

    def test_email_link_detector_does_not_follow_unrelated_or_unsafe_urls(self):
        grab = parse_posts.EmailLinks()
        grab.feed(''.join('<a href="' + url + '">Email</a>' for url in [
            "https://outlook.office.com.evil.invalid/mail/item",
            "https://evil.invalid/report.eml", "mailto:user@example.invalid",
            "javascript:alert(1)", "https://user@outlook.office.com/mail/item",
            "https://tenant.sharepoint.com/reports/original.eml",
        ]))
        self.assertEqual(grab.links, ["https://tenant.sharepoint.com/reports/original.eml"])

    def test_parser_blocks_unresolved_email_preview_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory(prefix="email-recovery-test-") as temp:
            root = pathlib.Path(temp)
            raw = root / "raw.json"
            raw.write_text(json.dumps([{"from_id": "sender", "created": "2026-07-01",
                                       "body": '<a href="https://outlook.office.com/mail/item">Email</a>'}]))
            output = root / "parsed.json"
            with self.assertRaisesRegex(SystemExit, "incomplete channel posts contain linked emails"):
                parse_posts.main(SimpleNamespace(inp=str(raw), config=str(SKILL / "config/team_config.json"),
                                                out=str(output), window_days=15, now="2026-07-02",
                                                generated=None))
            self.assertFalse(output.exists())

    def test_public_payload_suppresses_small_and_residual_cohorts(self):
        result = build_dashboard.public_data(private_data())
        current = result["aggregates"]["2026-10-01"]

        self.assertEqual(len(current["categories"]), 3)
        self.assertEqual(sum(item["tasks"] for item in current["categories"]), current["head"]["runTasks"])
        self.assertEqual([item["contributors"] for item in current["categories"]], [3, None, None])
        self.assertEqual([item["name"] for item in current["processes"]],
                         ["Technology & Engineering", "Strategy & Planning", "Sales & Customer Engagement"])
        self.assertEqual([item["contributors"] for item in current["processes"]], [3, None, None])
        self.assertEqual(sum(item["hours"] for item in current["processes"]), 25)
        self.assertEqual(sum(item["sessions"] for item in current["processes"]), 10)
        self.assertEqual([item["name"] for item in current["roleGroups"]], ["Data Analyst"])
        self.assertEqual([item["name"] for item in current["roles"]], ["Software Engineer"])
        self.assertEqual([item["grade"] for item in current["fit"]], ["H", "L"])
        self.assertEqual([item["contributors"] for item in current["fit"]], [3, None])
        self.assertEqual(sum(item["count"] for item in current["fit"]), 5)
        self.assertEqual(sum(item["count"] for item in current["fitDetails"]), 5)
        self.assertEqual(len(current["fitDetails"]), 3)
        self.assertEqual([item["contributors"] for item in current["fitDetails"]], [3, None, None])
        self.assertTrue(all(row["contributors"] is None or row["contributors"] >= 3 for row in current["categories"]))
        self.assertTrue(all(row["contributors"] is None or row["contributors"] >= 3 for row in current["processes"]))
        self.assertTrue(all(row["contributors"] is None or row["contributors"] >= 3 for row in current["fit"]))
        self.assertEqual(len(current["processDetails"]), 3)
        self.assertEqual(current["processDetails"][0]["type"], "HTML")
        self.assertEqual(current["processDetails"][0]["process"], "Technology & Engineering")
        self.assertEqual(verify_dashboard.verify_public_contract(result), [])
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
            attachment = temp / "team-dashboard-report.html"
            self.assertEqual(verify_dashboard.verify(str(attachment)), [])
            self.assertNotIn("</script><script>alert(1)", attachment.read_text().lower())

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
            self.assertIn('<a class="btn" href="team-summary.md" download>Export Markdown summary</a>', html)
            self.assertEqual(
                (page.parent / "assets/dashboard.js").read_bytes(),
                build_dashboard.dashboard_runtime().encode("utf-8"),
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
        self.assertNotIn("scripts/dashboard_runtime.py", source_files)
        self.assertIn("scripts/dashboard_assets.py", source_files)
        for name in source_files:
            self.assertEqual((SKILL / name).read_bytes(), (template / name).read_bytes(), name)
        self.assertFalse((template / "assets/dashboard.html").exists())
        self.assertFalse((template / "assets/dashboard.js").exists())

    def test_restored_assets_match_full_dashboard_release(self):
        import hashlib

        self.assertIn("exact contributor reach is withheld", build_dashboard.dashboard_markup())
        runtime = build_dashboard.dashboard_runtime()
        self.assertIn("of ${data.contributors} contributors", runtime)
        self.assertIn("${H.runTasks} run tasks", runtime)
        self.assertIn("<b>Total</b>", runtime)

    def test_standalone_attachment_works_without_companion_files_and_rejects_private_data(self):
        with tempfile.TemporaryDirectory(prefix="dashboard-attachment-test-") as temp:
            root = pathlib.Path(temp)
            data = root / "private.json"
            data.write_text(json.dumps(private_data()), encoding="utf-8")
            build_outputs.main(SimpleNamespace(inp=str(data), out_html=str(root / "site/index.html")))
            report = root / "attachment-only/report.html"
            report.parent.mkdir()
            report.write_bytes((root / "site/team-dashboard-report.html").read_bytes())
            self.assertEqual(verify_dashboard.verify(str(report)), [])
            html = report.read_text()
            self.assertNotIn("fetch(", html)
            self.assertNotIn('src="assets/', html)
            self.assertNotIn('href="assets/', html)
            self.assertNotIn("Secret contributor", html)
            self.assertNotIn('href="team-summary.md"', html)
            self.assertIn('id="report-glossary"', html)
            markup = verify_dashboard.AttachmentMarkup()
            markup.feed(html)
            public = json.loads(markup.scripts["report-data"])
            public["members"] = [{"email": "private@example.invalid"}]
            report.write_text(html.replace(markup.scripts["report-data"],
                                           build_dashboard.json_for_html(public)))
            self.assertTrue(verify_dashboard.verify(str(report)))

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

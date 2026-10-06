# Cowork Team Report — Team Dashboard

A Microsoft Copilot **Cowork skill** that rolls up a small team's Copilot Cowork ROI. It generates
**`output/team-dashboard/team-dashboard-report.html`**, a self-contained interactive attachment
for email to the requesting manager after recipient confirmation and approval. Download it and
open it in a full browser, not Cowork's or email's preview. No server or companion files are needed.
The optional multi-file site described below is retained for local use.

It reads the
de-identified stats each teammate emails to a shared Teams channel and renders **a private local site**
the manager can open, re-price with live controls, and print. HTML, CSS, JavaScript and public JSON
are separate files with no CDN dependencies. Share the verified standalone HTML, Markdown or PDF after
explicit approval; do not send the localhost URL or the multi-file site's `index.html`. The guide for
reading it is **built into the dashboard** — a **How to read** tab plus a clickable **"?"** on every
section — so there's no separate file to open. The bundled renderer produces four tabs:
**Overview**, **Impact & Value**, **How Cowork is used**, and **How to read + Glossary**. On first run
it **asks for the Teams channel link** and
remembers it; every run reads the **latest 15 days** of messages, keeping the latest report per person.

> **Team-safe by design.** The private working file contains per-contributor metrics for aggregation;
> it is not the report and must never be shared. The builder exports only team totals and breakdowns
> with the approved exceptions below; other breakdowns require the configured k-threshold. It excludes member records, task-level entries,
> deliverable names, raw filenames, prompts, and country. Small residual cohorts are suppressed unless
> the combined pool also meets the threshold.
>
> Approved exceptions: all category, business-process, service-role, team-wide skill and output-format totals are shown,
> while exact contributor reach below the threshold is omitted from the public data. These totals can
> reveal sparse work and are not fully k-anonymous. All Cowork-fit grade and expanded
> process/category totals follow the same exception. Other breakdowns remain suppressed.
> The category Total uses the same headline hours/run tasks as Overview.

## The three-skill family

| Skill | Role | Output |
|---|---|---|
| `cowork-roi-report` | A person's **full** personal impact report | Rich HTML web app (their own view) |
| `cowork-dashboard-member` | A person emails their **de-identified** stats to the team channel | HTML tables in Teams |
| **`cowork-dashboard-team-dashboard`** (this) | The **manager** aggregates everyone's reports | Self-contained HTML email report, plus optional local site and Markdown/PDF exports |

This skill **only consumes** what `cowork-dashboard-member` emails into the channel. It does not
harvest OneDrive. Sender IDs are used transiently to deduplicate posts and are not written to the
working JSON or dashboard.

## Scope (v1)

Small, **homogeneous** teams (people doing similar work) at the **team level** — a handful of
contributors on one channel. Org-wide / large-team / multi-channel aggregation is intentionally out
of scope for now.

## Data flow

```
first run: user pastes channel link ──(scripts/resolve_channel.py)──▶  team_id + channel_id  ──▶ config

teammates ──(cowork-dashboard-member email)──▶  Teams channel  ──(ListChannelMessages)──▶  raw_messages.json
                                                                                     │
                                                              scripts/parse_posts.py │  (last 15 days,
                                                              + process_groups.json  │   latest per sender,
                                                              + skills_vocabulary    │   group processes,
                                                              + skill_aliases         ▼   private intermediate)
                                                                                team_data.json (keep private)
                                                                                     │
                                     scripts/build_outputs.py ──▶ build_dashboard.py │  (aggregate-only payload,
                                     (guide built into the dashboard's               ▼   cohort filters, live rate)
                                      "How to read" tab)              output/team-dashboard/index.html
                                                                                     │
                                                          serve_dashboard.py ──▶ localhost browser
                                                          reviewed Markdown/PDF export ──▶ approved sharing
```

## Quick start

Channel email previews may omit report tables. The skill automatically reads the exact linked
original email through authorized host tools, validates the de-identified report and replaces the
partial body in a private hydrated input while preserving channel sender/time metadata. It never
crawls mailbox history or double-counts preview and email. Unreadable or ambiguous links block
completion with an explicit error. `parse_posts.py --inspect-email-links` lists body-link recovery
requests; the host also checks attachment/card references.

1. **Point it at the channel** (first run only). The skill asks for the **link of the Teams channel**
   where the team emails its Cowork Team Report stats (in Teams: channel ⋯ → *Get link to channel*), then
   resolves + saves the IDs:
   ```bash
   python scripts/resolve_channel.py --link "<pasted channel url>" --config config/team_config.json
   ```
   The Team must already exist and you must be a member. The channel **must match** the one
   whose email address is configured in `cowork-dashboard-member`. (See `SKILL.md → First run`.)
2. **Read + build (last 15 days) — dashboard + guide in one step:**
   ```bash
   # after saving the channel messages' `value` array to working/raw_messages.json
   python scripts/parse_posts.py --in working/raw_messages.json \
          --config config/team_config.json --out working/team_data.json --window-days 15
   python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
   ```
   This command uses the bundled renderer and runs `verify_dashboard.py`. It fails if any required
   aggregate visual, control, tab, or privacy check is missing.
3. **Open the self-contained report.** Download `output/team-dashboard/team-dashboard-report.html`
   and open it in a full browser. The skill verifies and offers to email this file to your confirmed
   address; a separate send approval is required. If email tools are unavailable it provides a download
   and explicitly states that email was not sent.

   **Optional local site:** Requires Python 3.9+ (no new runtime or package install):
   ```bash
   python scripts/serve_dashboard.py --dir output/team-dashboard
   ```
   It binds only to `127.0.0.1:7333` and opens the browser. Use `--no-open` for headless runs,
   or `--port 7334` if the default port is occupied. Stop with Ctrl+C. Do not open the HTML file
   directly for the multi-file site: its separate JSON files require HTTP. The self-contained report
   does not have this restriction. No desktop icon or start-at-login is installed.
4. **Verify before sharing.** When browser tools are available, open the standalone attachment, visit all four
   tabs, exercise the controls, expand a process drill-down, and verify the waterfall, category bars,
   stacked mix, and time/value toggle. Use screenshot verification when available; disclose when it
   is unavailable. A failed check blocks delivery.
5. **Review and email the HTML report.** Confirm your email address and approve the verified attachment.
   The optional local site also offers Export Markdown summary to download `team-summary.md` (default
   pricing), or use Save / Print PDF (current controls). Read the export, confirm recipients,
   then explicitly approve sharing. Builds and scheduled runs no longer email automatically.

The server serves only known public site files, rejects invalid Host/origin/path requests, and
has no command endpoints. Raw messages, working JSON and configuration are never served.
"Local" describes the site: Teams tools and the model still process input, and exports/backups
can leave the device. Use an approved agent and storage. This architecture change is not a
Microsoft Defender clearance; do not disable antivirus or add exclusions.

The full HTML markup and JavaScript are compressed, Base64-encoded strings in
`scripts/dashboard_assets.py`, decoded by `scripts/build_dashboard.py` at build time.
Building the report produces
ordinary `index.html` and `assets/dashboard.js` files.
This packaging change has not been confirmed to resolve Defender warnings.

## Mandatory dashboard contract

- Build only with `scripts/build_outputs.py`; never substitute a simplified layout.
- The parser's `working/team_data.json` is an internal intermediate containing contributor-level
  metrics. Do not email, publish, or attach it. The renderer constructs a separate public aggregate
  contract before writing public JSON.
- All category, business-process, service-role, team-wide skill and output-format totals are included, with exact
  reach redacted below the threshold. No top-N limit hides service roles. The expandable skills
  table contains team-wide skills, not an inferred per-role attribution.
- All reported Cowork-fit grades and expanded process/category totals are included with exact
  small contributor reach redacted. Totals sum reported graded tasks, not ungraded headline tasks.
- All process output-type totals are shown, grouped by process/type with counts and summed
  hours/value; exact small reach is redacted. No global format totals are attributed to a process
  without supporting process-level source data.
- Each input/output mix, process skill detail, and role-category mix is included
  only when at least `privacy_k_threshold` contributors support it. Small residual role groups are
  combined only when the pooled group also meets that threshold; otherwise they are omitted.
- The local site never includes member records, individual roles, task descriptions, deliverable names,
  per-deliverable rows, or contributor-to-category links. Process drill-downs contain cohort-qualified
  format and skill totals only.
- Required visuals: Cowork-fit waterfall, category bars, stacked category mix, expandable
  business-process drill-downs, and the time/value toggle.
- `scripts/verify_dashboard.py` must pass before email delivery.
- If any required visual or control is missing or broken, fix and rebuild instead of sending an
  incomplete dashboard or calling the run complete.

### Try it offline (no Teams needed)

Two real, de-identified channel messages are bundled:

```bash
python scripts/parse_posts.py --in examples/sample_raw_messages.json \
       --config config/team_config.json --out working/team_data.json \
       --window-days 15 --now 2026-07-02 --generated 2026-07-01
python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
python scripts/serve_dashboard.py --dir output/team-dashboard
```

## Config (`config/team_config.json`)

| Key | Meaning |
|---|---|
| `team_id`, `channel_id` | Where to read (authoritative). **Blank until first run**, then filled by `resolve_channel.py` from the pasted link. |
| `channel_link` | The Teams channel URL the user pasted on first run (kept for reference). |
| `hourly_rate` | Default $/hr for the value model (adjust live in the UI). |
| `recapture_rate` | Productivity recapture rate `0–1` (default **0.70**): the share of time saved the team realistically harvests. Value = time saved × recapture rate × hourly rate. Adjustable live in the UI. |
| `cadence_days` | Report/refresh cadence (default 14). |
| `message_lookback_days` | Window each run reads — **default 15** (the latest cycle). Enforced by `--window-days`. |
| `privacy_k_threshold` | Minimum contributors sharing an attribute before it breaks out (default 3). |
| `email_on_run` | Legacy setting, now false by default. True may offer to share, but never authorizes sending; exports always require review and explicit approval. |
| `team_size` | Optional; v1 shows a contributor count, not adoption %. |

## Privacy model

- Members are **counts + a number**, never named.
- Before emailing the report to the channel, each member can remove any session they do not want included. Its
   artifacts are removed with it before metrics are computed; the original Cowork session is not deleted.
- The private working JSON contains the directory **Role** and per-contributor statistics for
   aggregation; neither the Role assignments nor individual records are published.
- **Approved exceptions:** category, business-process, service-role, team-wide skill and output-format totals include
   low-support rows, as do Cowork-fit grade/process/category totals, but exact reach is redacted below `privacy_k_threshold`.
- **Cohort threshold:** other breakdowns require ≥ `privacy_k_threshold` distinct contributors.
   Secondary details and small residual directory-role groups remain suppressed.

## Shared taxonomy contract (keep in sync)

`process_groups.json`, `skills_vocabulary.json`, `roles_taxonomy.json`, and
`references/value-pillars.md` are **byte-for-byte mirrors** of the `cowork-dashboard-member` bundle (which
in turn mirrors `cowork-roi-report`). If those change, update this copy too or team aggregation
drifts. `skill_aliases.json` is reader-only and not part of the contract.

**Deliverable detail:** contributor-level names, dates, and rows are never published. The dashboard
shows all aggregate counts and hours grouped by a standard file format in Impact & Value. Within
a process, all reported format totals are shown; skills still require `privacy_k_threshold`
distinct contributors.
The output-format Total sums the reported format rows; it does not substitute the headline count.

## Requirements

- Python 3.9+. The whole default pipeline (`resolve_channel.py`, `parse_posts.py`, `build_dashboard.py`,
  `verify_dashboard.py`, `build_outputs.py`) is **standard library only** — the how-to-read guide is rendered inside the
  dashboard, so no extra dependency is needed. The **legacy** `build_guide_pdf.py` uses **reportlab**
  (pre-installed in the Copilot Cowork container) and only runs if you pass `--with-pdf`.
- Runs inside Microsoft Copilot Cowork (Teams + email tools provided by the host). The scripts
  themselves run anywhere Python 3 does.

## License

Add your license of choice (e.g. MIT) before publishing externally.

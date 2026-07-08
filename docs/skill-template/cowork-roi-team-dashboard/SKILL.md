---
name: cowork-roi-team-dashboard
description: |
  Manager-side team rollup for Copilot Cowork ROI. Aggregates the de-identified stats teammates post (via the Copilot ROI Member skill) to a shared Teams channel into ONE anonymized HTML dashboard (five tabs), then emails the channel members a summary with the dashboard and a one-page PDF guide attached. First run asks for the Teams channel link and remembers it; each run reads the latest 15 days and keeps the latest post per person. Numbers only — no names or files; a Role breaks out only when 3+ share it. Small homogeneous teams; not org-wide.
  Use when the user asks to "build the team Cowork ROI dashboard", "aggregate my team's Cowork stats", "roll up the channel posts", "manager Cowork ROI report", "email the team dashboard", or set up / refresh the rollup.
  Do NOT use for: the personal report (cowork-roi-report), a member's own post (cowork-roi-member), the member-side aggregated post (cowork-roi-report-aggregated), org-wide/large-team aggregation, GitHub Copilot reports, or single-meeting summaries.
cowork:
  category: analysis
  icon: BarChart4
---

# Cowork ROI — Team Dashboard (manager rollup)

Aggregates the **de-identified Cowork ROI posts** teammates publish (via the **Copilot ROI
Member** skill, `cowork-roi-member`) to a shared Teams channel, renders a single self-contained,
**anonymized** HTML dashboard, and **emails the channel members** a high-level summary with the
dashboard and a one-page interpretation guide (PDF) attached.

**This skill only reads what the Member skill posts.** It never harvests anyone's OneDrive and
never sees names, files, or prompts. If a label (business process, skill, Role) doesn't match the
Member bundle's copy, aggregation drifts — the taxonomy files here are **byte-for-byte mirrors** of
the Member skill's (see *Cross-skill contract*).

## Scope (v1)
- **Small, homogeneous teams** (people doing similar work), **team level**. A handful of
  contributors sharing one channel.
- **Not** org-wide / large-team / multi-channel aggregation, and **not** cross-team benchmarking.

## When NOT to Use
- **A single person's full impact report** → `cowork-roi-report` (rich personal web app).
- **Posting your own de-identified stats** to the channel → `cowork-roi-member`.
- **The member-side anonymized table post** → `cowork-roi-report-aggregated`.
- **Org-wide / multi-team / cross-channel aggregation** — out of scope for v1; don't force it.
- **GitHub Copilot / IDE usage reports**, **daily briefings**, or **single-meeting summaries** —
  different skills entirely.
- If the shared channel has **no Cowork ROI posts in the last 15 days**, don't fabricate a dashboard —
  say the window was empty and offer to widen it.

## First run — point the skill at the channel (once)

The rollup reads ONE shared Teams channel that teammates post to. The channel is **not hard-coded**.

1. **Load `config/team_config.json`.** If `team_id` **or** `channel_id` is blank, this is a first run.
2. **Ask for the channel link.** Use `AskUserQuestion` to ask the user to paste the **link of the
   Teams channel** where the team posts its Cowork ROI stats (in Teams: channel ⋯ → *Get link to
   channel*). This must be the same channel `cowork-roi-member` posts to.
3. **Resolve + persist the IDs** from that link — no Graph call needed:
   ```
   python scripts/resolve_channel.py --link "<pasted url>" --config config/team_config.json
   ```
   It extracts `channel_id` (the `19:…@thread.…` segment) and `team_id` (the `groupId`), writes them
   plus `channel_link` back to the config, and every later run reads the same place. Optionally call
   `GetTeam(team_id)` and save its `displayName` as `team_name` so the dashboard header is named.
4. **The Team must already exist** and the runner must be a **member** of it
   (`ChannelMessage.Read.All`). This skill does not create Teams or channels. If a read fails with an
   authorization error, the runner isn't a member — add them in Teams; the skill can't grant access.

On later runs `team_id` + `channel_id` are already set, so skip straight to the workflow. Re-ask for a
link only if the user wants to point at a **different** channel.

## Workflow

### 1. Load config (+ first-run channel link)
Read `config/team_config.json`. If `team_id`/`channel_id` are blank, run **First run** above.

### 2. Read the channel posts (latest 15 days)
`ListChannelMessages(team_id, channel_id, top=50)` (paginate with `next_link` if the team is chatty).
Save the returned `value` array verbatim to `working/raw_messages.json` (the parser accepts the Graph
message shape directly). The **latest-15-days window** and **latest-post-per-person** dedupe are
applied in step 3 — don't hand-filter here.

### 3. Parse + aggregate (window, anonymize, group, canonicalize)
```
python scripts/parse_posts.py --in working/raw_messages.json --config config/team_config.json \
       --out working/team_data.json --window-days 15 [--now YYYY-MM-DD] [--generated YYYY-MM-DD]
```
`parse_posts.py`:
- keeps only posts from the **last 15 days** (`--window-days`, anchored to `--now`/today), then keeps
  the **latest post per sender** (id hashed away, never stored/shown), numbering contributors 1..N;
- reads each post's parser-stable tables by header signature (tolerant of metric wording drift);
- pulls the **Role** line if present (the only attribute — no names, no country, no files);
- **groups business processes** (`process_groups.json`) and **canonicalizes skills**
  (`skills_vocabulary.json` + `skill_aliases.json`);
- writes `working/team_data.json` (meta + one snapshot + members[] with role|null + metrics).

### 4. Build the dashboard
```
python scripts/build_dashboard.py --in working/team_data.json \
       --out output/cowork-team-roi-dashboard.html
```
Self-contained HTML (no external assets). Five small tabs: **Overview** (auto-insights + KPI band) ·
**Impact & Value** (pillars, categories with $, roles, deliverables by type) · **How Cowork is used**
(business-process leads, skills, category mix, analyzed → produced) · **Trends** (minimal
fortnight-over-fortnight line) · **Glossary & method**. Value = hours × rate, recomputed live by a
rate control.

### 5. Build the one-page interpretation guide (PDF)
```
python scripts/build_guide_pdf.py --out output/how-to-read-team-roi-dashboard.pdf \
       --data working/team_data.json --config config/team_config.json
```
A single **landscape** page explaining every KPI, the five tabs, the two controls, the privacy model,
and the methodology — so recipients can read the dashboard unaided. Uses `reportlab` (bundled in the
Cowork container).

### 6. Email the channel members (summary + both attachments)
If `email_on_run` is true (default) and the user hasn't said "don't send":
- **Recipients = the channel members.** `ListChannelMembers(team_id, channel_id)` → resolve each to an
  email/UPN; de-duplicate; include the runner. (A standard channel returns the team members — that's
  the intended audience.) Never add anyone outside the channel.
- **Body = a high-level HTML summary** (aggregate only, same privacy rules as the dashboard). Pull the
  figures from `working/team_data.json` — sum the members' headline metrics (time saved, value =
  hours × rate, sessions, run tasks, deliverables) and name the top 1–2 business processes. Do **not**
  hand-invent numbers; if a figure isn't in the data, omit it.
- **Send** with both attachments:
  ```
  SendEmailWithAttachments(
    to=<resolved channel-member emails>,
    subject="Team Cowork ROI dashboard — latest rollup (<period>)",
    content_type="HTML", body=<summary html>,
    direct_attachment_file_paths=["output/cowork-team-roi-dashboard.html",
                                  "output/how-to-read-team-roi-dashboard.pdf"])
  ```
  In interactive runs the platform's approval dialog is the confirmation; scheduled runs send
  automatically. The "Powered by Copilot Cowork" footer is appended by the host — don't add your own.

### 7. Verify + deliver
`Glob output/cowork-team-roi-dashboard.html` and `Glob output/how-to-read-team-roi-dashboard.pdf` to
confirm both exist, then tell the user they're saved and the email went to the channel members.
Optionally show a 3-line highlight (time saved, value, top process) — aggregate only.

### 8. (Optional) automate
If the user asks, `SetupScheduledPrompt` (frequency **Day**, interval = `cadence_days`, hours `["9"]`,
name "Cowork ROI team dashboard") with a self-contained description: *"Read the last 15 days of Cowork
ROI posts in the team channel, aggregate them into the anonymized team dashboard and one-page PDF
guide, save them to my files, and email them to the channel members."* Align the cadence with the
Member skill's 15-day post cycle (run a day or two after).

## Privacy (hard rules)
- **Never show anything at an individual level.** Members are counts + a number only.
- **k-anonymity:** a per-attribute (Role) breakdown renders only when **≥ `privacy_k_threshold`**
  (default **3**) contributors share that Role; otherwise those contributors collapse into a single
  combined bar. Small homogeneous teams usually render one combined bar — that's correct.
- **Attributes:** only the directory **Role** a post carries. **Never** names, country, file names,
  prompts, or JTBD prose. The parser doesn't read them and the dashboard can't show them.
- **The email body is aggregate-only too** — same rules; no member is ever named or singled out.
- The whole artifact is **team-safe / shareable** — it exposes totals and the generic shape of work,
  never who did what.

## Cross-skill contract (keep in sync)
This skill can only aggregate what **`cowork-roi-member`** posts. These must match its copies or
aggregation breaks — **change them in both bundles together**:

| Item | This skill | Must match |
|---|---|---|
| Business-process **grouping** | `scripts/process_groups.json` | `cowork-roi-member/scripts/process_groups.json` (and `cowork-roi-report`'s copy) — **byte-for-byte** |
| **Skills** vocabulary | `scripts/skills_vocabulary.json` | `cowork-roi-member/scripts/skills_vocabulary.json` (and `cowork-roi-report`'s) — **byte-for-byte** |
| **Roles** taxonomy | `scripts/roles_taxonomy.json` | `cowork-roi-member/scripts/roles_taxonomy.json` — **byte-for-byte** |
| **Value pillars** | `references/value-pillars.md` | `cowork-roi-member/references/value-pillars.md` — **byte-for-byte** |
| **Role** attribute + no country/names | reads the post header `Role:` line | `cowork-roi-member/scripts/format_member_message.py` (emits `Role:`; excludes country/names) |
| Deliverable → process link + **by-type** rollup | parser reads the "By type" deliverables table | `format_member_message.py` (that rollup "is also what the aggregated Dashboard reads") |
| The **shared channel** | `channel_id` resolved from the link the user pastes | the channel `cowork-roi-member` posts to (its SKILL.md → *Target channel*) — must be the same channel |

- `scripts/skill_aliases.json` is a **reader-only** compatibility shim (maps older non-canonical skill
  labels → the vocabulary). It is **not** part of the shared contract and lives only here.
- **Deliverable NAMES:** the Member skill **strips file names by design** (emits
  Type/Date/Process/Skills/Hours/Value — no names). To show doc names, the Member skill must first add
  an opt-in name manifest; only then can this reader surface a manager-only named list. That is a
  **Member-skill change** — flag it before promising named deliverables.

## Guardrails
- **No fabricated data.** Every number traces to a post via the pipeline. Empty sections are omitted;
  an empty 15-day window yields no dashboard, not a made-up one.
- **No hand math.** `parse_posts.py` totals; `build_dashboard.py` prices at the live rate; the email
  figures are read from `team_data.json`.
- **Self-contained output.** The HTML embeds all CSS/JS/data — no external assets.
- **Latest post wins, within the window.** The reader keeps only the last 15 days, then the most
  recent post per sender; re-running a member's post replaces their earlier contribution.
- **Channel is user-owned.** Read the channel resolved from the user's link; re-ask only if they name
  a different one. Never guess or construct a `channel_id`.
- **Email stays inside the channel.** Recipients are the channel members only; the body is
  aggregate-only. Interactive sends go through the approval dialog; honor "don't email" / `email_on_run:false`.

## Bundled files
- `SKILL.md`, `README.md`, `CHANGELOG.md`
- `config/team_config.json` — rate + k-threshold + cadence + 15-day lookback + email toggle; the
  channel IDs are filled in on first run (not shipped hard-coded).
- `scripts/resolve_channel.py` — parse a pasted Teams channel/message link → `team_id` + `channel_id`; persist to config (stdlib only).
- `scripts/parse_posts.py` — channel posts → anonymized `team_data.json` (stdlib only; 15-day window, latest-per-sender, groups processes, canonicalizes skills, k-anon-ready).
- `scripts/build_dashboard.py` — `team_data.json` → self-contained HTML dashboard (stdlib only).
- `scripts/build_guide_pdf.py` — one-page landscape interpretation PDF (uses `reportlab`, bundled in Cowork).
- `scripts/process_groups.json`, `scripts/skills_vocabulary.json`, `scripts/roles_taxonomy.json` — **mirrors** of the Member bundle (shared contract).
- `scripts/skill_aliases.json` — reader-only skill-label compatibility shim.
- `references/value-pillars.md` — **mirror** of the four-pillar crosswalk.
- `examples/sample_raw_messages.json` — two real, de-identified posts for an offline end-to-end test.

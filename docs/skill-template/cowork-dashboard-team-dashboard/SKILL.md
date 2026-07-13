---
name: cowork-dashboard-team-dashboard
description: |
  Manager-side team rollup for Copilot Cowork ROI. Aggregates the de-identified stats teammates post (via the Cowork Team Report Member skill) to a shared Teams channel into ONE anonymized HTML dashboard (five tabs, with the how-to-read guide built in), then emails the channel members a summary with the dashboard attached. First run asks for the Teams channel link and remembers it; each run reads the latest 15 days and keeps the latest post per person. Numbers only — no names or files; a Role breaks out only when 3+ share it. Small homogeneous teams; not org-wide.
  Use when the user asks to "build the team Cowork Team Report", "aggregate my team's Cowork stats", "roll up the channel posts", "manager Cowork Team Report", "email the team dashboard", or set up / refresh the rollup.
  Do NOT use for: the personal report (cowork-roi-report), a member's own post (cowork-dashboard-member), the member-side aggregated post (cowork-roi-report-aggregated), org-wide/large-team aggregation, GitHub Copilot reports, or single-meeting summaries.
cowork:
  category: analysis
  icon: BarChart4
---

# Cowork Team Report — Team Dashboard (manager rollup)

Aggregates the **de-identified Cowork Team Report posts** teammates publish (via the **Copilot ROI
Member** skill, `cowork-dashboard-member`) to a shared Teams channel, renders a single self-contained,
**anonymized** HTML dashboard, and **emails the channel members** a high-level summary with the
dashboard attached. The interpretation guide is **built into the dashboard** (the **How to read**
tab, plus a clickable **"?"** on every section title) — there is no separate PDF attachment by
default, so recipients read everything in one file.

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
- **Posting your own de-identified stats** to the channel → `cowork-dashboard-member`.
- **The member-side anonymized table post** → `cowork-roi-report-aggregated`.
- **Org-wide / multi-team / cross-channel aggregation** — out of scope for v1; don't force it.
- **GitHub Copilot / IDE usage reports**, **daily briefings**, or **single-meeting summaries** —
  different skills entirely.
- If the shared channel has **no Cowork Team Report posts in the last 15 days**, don't fabricate a dashboard —
  say the window was empty and offer to widen it.

## First run — point the skill at the channel (once)

The rollup reads ONE shared Teams channel that teammates post to. The channel is **not hard-coded**.

1. **Load `config/team_config.json`.** If `team_id` **or** `channel_id` is blank, this is a first run.
2. **Ask for the channel link.** Use `AskUserQuestion` to ask the user to paste the **link of the
   Teams channel** where the team posts its Cowork Team Report stats (in Teams: channel ⋯ → *Get link to
   channel*). This must be the same channel `cowork-dashboard-member` posts to.
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

### 4. Build the dashboard (guide built in)
```
python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
```
Renders the single deliverable:
- **`output/cowork-team-roi-dashboard.html`** — self-contained HTML (no external assets). Five small
  tabs: **Overview** (auto-insights + KPI band) · **Impact & Value** (pillars, categories with $ and
  **contributor reach** per category, roles, deliverables by format) · **How Cowork is used**
  (business-process accordion — each process expands to its deliverables, with **type-only items
  collapsed per format** e.g. "HTML · 5 deliverables" — category mix, analyzed → produced) ·
  **Trends** (minimal fortnight-over-fortnight line) · **How to read** (the full in-dashboard guide:
  every KPI, the five tabs, the two controls, how task categories are derived, the privacy model, and
  the methodology). Every section title also carries a clickable **"?"** popover. Value = hours ×
  rate, recomputed live by a rate control.

The **How to read** tab replaces the old standalone one-page PDF — the guide now travels *inside* the
dashboard, so there is nothing separate to notice or toggle to. `build_outputs.py` just drives
`build_dashboard.py` (still runnable on its own). The legacy PDF (`build_guide_pdf.py`) is retained
but **off by default**; pass `--with-pdf` to `build_outputs.py` only if someone explicitly wants a
printable copy.

### 5. Email the channel members (summary + dashboard attachment) — a separate, expected approval
The email send is deliberately **not** bundled into step 4: building the file is one approval, and
sending it to people is a second, distinct approval. If `email_on_run` is true (default) and the
user hasn't said "don't send":
- **Recipients = the channel members.** `ListChannelMembers(team_id, channel_id)` → resolve each to an
  email/UPN; de-duplicate; include the runner. (A standard channel returns the team members — that's
  the intended audience.) Never add anyone outside the channel.
- **Body = a high-level HTML summary** (aggregate only, same privacy rules as the dashboard). Pull the
  figures from `working/team_data.json` — sum the members' headline metrics (time saved, value =
  hours × rate, sessions, run tasks, deliverables) and name the top 1–2 business processes. Do **not**
  hand-invent numbers; if a figure isn't in the data, omit it.
- **Send** with the dashboard attached (the guide is inside it — no separate PDF):
  ```
  SendEmailWithAttachments(
    to=<resolved channel-member emails>,
    subject="Team Cowork Team Report — latest rollup (<period>)",
    content_type="HTML", body=<summary html>,
    direct_attachment_file_paths=["output/cowork-team-roi-dashboard.html"])
  ```
  In interactive runs the platform's approval dialog is the confirmation; scheduled runs send
  automatically. The "Powered by Copilot Cowork" footer is appended by the host — don't add your own.

### 6. Verify + deliver
`Glob output/cowork-team-roi-dashboard.html` to confirm it exists, then tell the user it's saved and
the email went to the channel members.
Optionally show a 3-line highlight (time saved, value, top process) — aggregate only.

### 7. (Optional) automate — run 1–2 days after the member fortnight
If the user asks, `SetupScheduledPrompt` with a self-contained description: *"Read the last 15 days of
Cowork Team Report posts in the team channel, aggregate them into the anonymized team dashboard (the how-to-read
guide is built into it), save it to my files, and email it to the channel members."*

**Timing:** the Member skill posts on a **biweekly Monday** cycle, so schedule the manager rollup to
run **1–2 days later — on Wednesday** — which gives teammates Monday and Tuesday to post before the
rollup reads the channel. Use frequency **Week**, `interval = cadence_days / 7` (= **2** → every other
Wednesday), `weekDays=["Wednesday"]`, `hours=["9"]`, name "Cowork Team Report team dashboard". Scheduled runs
build the dashboard and email the channel members automatically (no interactive approval).

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
This skill can only aggregate what **`cowork-dashboard-member`** posts. These must match its copies or
aggregation breaks — **change them in both bundles together**:

| Item | This skill | Must match |
|---|---|---|
| Business-process **grouping** | `scripts/process_groups.json` | `cowork-dashboard-member/scripts/process_groups.json` (and `cowork-roi-report`'s copy) — **byte-for-byte** |
| **Skills** vocabulary | `scripts/skills_vocabulary.json` | `cowork-dashboard-member/scripts/skills_vocabulary.json` (and `cowork-roi-report`'s) — **byte-for-byte** |
| **Roles** taxonomy | `scripts/roles_taxonomy.json` | `cowork-dashboard-member/scripts/roles_taxonomy.json` — **byte-for-byte** |
| **Value pillars** | `references/value-pillars.md` | `cowork-dashboard-member/references/value-pillars.md` — **byte-for-byte** |
| **Role** attribute + no country/names | reads the post header `Role:` line | `cowork-dashboard-member/scripts/format_member_message.py` (emits `Role:`; excludes country/names) |
| Deliverable → process link + **by-type** rollup | parser reads the "By type" deliverables table | `format_member_message.py` (that rollup "is also what the aggregated Dashboard reads") |
| The **shared channel** | `channel_id` resolved from the link the user pastes | the channel `cowork-dashboard-member` posts to (its SKILL.md → *Target channel*) — must be the same channel |

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
- `scripts/build_dashboard.py` — `team_data.json` → self-contained HTML dashboard with the guide built in (stdlib only): the **How to read** tab, per-section **"?"** helpers, per-category **contributor reach** (with a `<k` privacy floor), and **type-only deliverables collapsed per format**.
- `scripts/build_guide_pdf.py` — **legacy** one-page landscape interpretation PDF (uses `reportlab`). Retained but off by default; the guide now lives inside the dashboard.
- `scripts/build_outputs.py` — the build step; renders the dashboard (guide built in). Pass `--with-pdf` to also regenerate the legacy PDF.
- `scripts/process_groups.json`, `scripts/skills_vocabulary.json`, `scripts/roles_taxonomy.json` — **mirrors** of the Member bundle (shared contract).
- `scripts/skill_aliases.json` — reader-only skill-label compatibility shim.
- `references/value-pillars.md` — **mirror** of the four-pillar crosswalk.
- `examples/sample_raw_messages.json` — two real, de-identified posts for an offline end-to-end test.

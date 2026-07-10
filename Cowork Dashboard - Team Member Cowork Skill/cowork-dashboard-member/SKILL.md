---
name: cowork-dashboard-member
description: |
  Member step of the team Cowork Dashboard rollup. Harvests the signed-in user's own Copilot Cowork session history from OneDrive, lets the user exclude any chat/task, computes impact metrics, and posts a de-identified, TABLE-FORMATTED stats message to your team's dedicated "Cowork report" Teams channel (the channel link is requested on first run and remembered). Tables cover KPIs, time-by-category, value pillars, jobs-to-be-done, business processes, roles, skills, and deliverable types. Person names, file names and prompts are excluded; process/JTBD and customer/account names are kept. Bundles its own pipeline. Runs once or on a biweekly schedule (every other Monday; scheduled runs email the user to review/exclude sessions before posting).
  Use when the user asks to "post my Cowork Dashboard stats", "send my Cowork stats to the team channel", "run the Cowork Dashboard member step", or "share my Cowork impact with the team".
  Do NOT use for: the full personal HTML report (use cowork-roi-report), the manager-side team dashboard, GitHub Copilot reports, or single-meeting summaries.
cowork:
  category: productivity
  icon: PeopleTeam
---

# Cowork Dashboard — Member step (de-identified table post to the team channel)

Produces the **per-person, de-identified** input to a team Cowork Dashboard, rendered as
**HTML tables** so it's both readable in Teams and easy for a downstream Cowork task to parse.
**No person names, file names or prompts leave the machine** — the post carries aggregate totals,
task categories, value pillars, roles, skills, deliverable/IO breakdowns, and the de-duplicated
**Jobs-to-be-done** and **Work-by-business-process** tables (which may carry customer/account names —
those are in scope; only people's names are stripped).

## Prerequisites — none (self-contained)
This skill bundles its **own** analysis pipeline (`classify.py`, `compute.py`, the
`reconcile_taxonomy.py` memory step, taxonomy data, and the harvest references).
It does **not** depend on `cowork-roi-report` or any other skill being installed. A new user just
drops the single `cowork-dashboard-member/` folder into their Cowork skills directory
(`Documentos/Cowork/skills/`) and runs it — nothing else to install. It keeps a **per-user, durable
taxonomy memory** at `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json` — scoped to
the invoking user (owner-stamped) and stored on their own mount (syncs to their OneDrive Cowork
folder). **There is NO bundled seed and nothing user-specific ships in the folder:** a first run
starts with no memory and mints the user's processes from their OWN sessions.

## When to use
- "Post my Cowork Dashboard stats to the team channel" / "run the Cowork Dashboard member step"
- A team cadence (e.g. every other Monday) where each member contributes their stats.

## When NOT to use
- Full personal HTML report with project detail → `cowork-roi-report`.
- Gathering everyone's posts into the team dashboard → the manager skill.

## Target channel — asked on first run, then remembered
This skill posts to **one Teams channel that your team's admin / manager / lead created** for Cowork
reports (named e.g. `Cowork report - <team>`). It is **not hardcoded** — each member points the skill
at their team's channel once:

0. **Bundled team default.** Read `config/team_channel.json` in this skill's folder. If
   `channel_link` is non-empty (or `team_id` AND `channel_id` are both non-empty), use those IDs for
   posting, cache them to the per-user memory file
   (`/mnt/user-config/.claude/cowork-dashboard-member-channel.<userkey>.json`) so later runs converge on the
   normal path, and **SKIP asking**. If it's empty, fall through to the existing steps (reuse saved
   memory → else ask). This file ships **empty** in the bundle; a per-team copy is filled by the
   installer generator at download time so members never see the link prompt.
1. **Reuse a saved channel.** Look for the per-user memory file
   `/mnt/user-config/.claude/cowork-dashboard-member-channel.<userkey>.json` (`<userkey>` = the runner's
   `mail`). If present, reuse the stored `team_id` + `channel_id`.
2. **Otherwise, ask for the link.** With `AskUserQuestion`, ask the user to paste the **Teams channel
   link** their admin/manager/lead shared (in Teams: channel **⋯** → **Copy link**). Parse it:
   - `channel_id` = the path segment right after `/channel/`, URL-decoded (`%3A`→`:`, `%40`→`@`) →
     looks like `19:…@thread.tacv2`.
   - `team_id` = the `groupId` query parameter.
   Save both (owner-stamped) to the memory file above so later runs don't re-ask.
3. **Post** with `PostChannelMessage(team_id=…, channel_id=…, body=<html>)`. If an ID call fails, fall
   back to the `team_name`/`channel_name` parsed from the link.

**Never invent a channel.** If nothing is saved and the user can't provide a link, stop and tell them
to get the channel link from their team's admin/manager/lead (see the repo README's *First-time
setup*).

All script paths below are under this skill's own folder:
`/mnt/user-config/.claude/skills/cowork-dashboard-member/scripts/`.

## Workflow

### 1. Choose run mode + period
Ask once with **`AskUserQuestion`**: *"Run this once, or automate it every other Monday?"* — options
**"Just once"** / **"Automate biweekly on Mondays (email me to review before each post)"**. The period
defaults to the **last 15 days** (ask only if the user names a different window). Window = N days
ago 00:00 → today 23:59, local time. If they choose automate, still produce a post now **and** set
up the schedule in step 9.

> **Note:** This automate/schedule prompt appears on the **first RUN** of the skill, not at install.

### 2. Resolve identity & dates
`GetMyDetails(select="mail,userPrincipalName,displayName,jobTitle")` (the `mail` is the per-user memory
owner — passed to `reconcile_taxonomy.py --owner` in step 5; `jobTitle` becomes the runner's **Role**
attribute shown on the post — see step 3). compute `after` = N days ago 00:00 local, `before` =
today 23:59 local, `window.label` = "Last N days", `window.months` = N/30.
**Role, not identity:** carry the directory `jobTitle` only. Never add country, and never any person
name, file name, or prompt.

### 3. Harvest the user's Cowork sessions (self-contained)
Cowork persists each session's workspace to OneDrive under a `Cowork` store (commonly
`Documents/Cowork/`, but often localized/suffixed — `Documentos/Cowork`, `Cowork 1`, …). Harvest
ALL session folders in the window:
- `GetDefaultDrive()` → personal OneDrive `drive_id`.
- **Locate the Cowork folder** — try `GetDriveChildren(drive_id, item_path="/Documents/Cowork")`; on
  404, list `/Documents` (then the drive root, then `/Documentos/Cowork`) and pick the child whose
  name starts with `Cowork` (case-insensitive). Carry the resolved name forward.
- **Enumerate all three layouts** under it, following pagination (`@odata.nextLink`) to exhaustion:
  Task folders `<Cowork>/Tasks/<goal-slug>-<YYYY-MM-DD>/` (→ `input/`+`output/`), root goal folders
  `<Cowork>/<goal-slug>-<YYYY-MM-DD>/`, and legacy `<Cowork>/sessions/<uuid>/`.
- **Scope to the Cowork app** — count a folder/artifact ONLY when its `createdBy.application.id` is
  the Cowork app id `6ab48b67-cd74-4ad4-81af-5932984589be` (Cowork's fixed **product** app ID — the same for every user and tenant; leave it as-is, it is NOT a value to fill in). **Never** enumerate `Documents/Apps/…`
  (a different product).
- Keep session folders whose created/modified date is in the window. For each, list its `output/`
  (and `input/`) for artifact names + extensions. **Fold supporting files** (QA screenshots,
  `-v2`/`-sample` variants, prompts, READMEs, lock files, zips) into the session's primary
  deliverable. Keep output-less (chat-only) sessions.
- **Deliverable `name` = a clean, de-identified DESCRIPTIVE label — NOT the raw file name.** For each
  output, write a short readable label (e.g. `ROI newsletter`, `AI-in-One insights deck`, `Clinic
  operations dashboard`) with the extension, person names, and any customer/account names stripped.
  This `name` is shown verbatim in the **Deliverable** column of the posted table (§7.9), so it must
  carry NO personal or customer identifier and NO raw filename. (Keep the real `ext` — it drives
  classification.)
- Write `working/cowork_raw.json`:
  ```json
  { "meta": {"user":"<name>","email":"<mail>","role":"<jobTitle from step 2>","generated":"<YYYY-MM-DD>",
             "window":{"from":"...","to":"...","label":"Last N days","months":0.5},"hourly_rate":72},
    "sessions": [ {"id":"<slug>","date":"YYYY-MM-DD","hour":12,"goal":"<short verb-first phrase>",
                   "inputs":[{"name":"report.pdf","ext":"pdf"}],
                   "outputs":[{"name":"AI-in-One insights deck","ext":"pptx","skills":["Presentation Design"]}],
                   "skills":["Data Analysis"], "professional_roles":["Data Analyst"],
                   "has_folder":true, "exec_min":null} ] }
  ```
Do **not** classify/compute yet — the user prunes first.

### 4. Privacy opt-out — let the user remove any chat/task BEFORE anything is computed
**Mandatory, every run, before classify/compute.** Nothing about an excluded session is ever
classified, costed, named, or posted.
1. List the inventory: `python .../scripts/prune_sessions.py --in working/cowork_raw.json --list`
   (one numbered line per session, between `<<<COWORK-SESSION-INVENTORY>>>` markers).
2. **Interactive run:** ask which to leave out with an **`AskUserQuestion` card, `multiSelect: true`**
   — each option is one session (label = short goal + date). When you show the picker, include a short
   **reminder to exclude anything personal or non-work they're not comfortable sharing** with the team
   before it posts (each session's deliverables go out with it). `prune_sessions.py --list` prints this
   same reminder. `AskUserQuestion` allows 4 questions × 4 options (16 sessions) per call, so **page
   through ALL sessions** across consecutive rounds of 16 (30 → 2 rounds; tell the user "1 of 2") —
   every chat/task must be individually selectable; never show only a subset. Selecting nothing = keep
   everything.
3. **Scheduled run (no interactive user):** do **not** show the picker (it would hang). Compute the
   draft and **email the user to review/exclude in the task chat** (see step 9) — never post without
   the user's opt-out.
4. Apply: `python .../scripts/prune_sessions.py --in working/cowork_raw.json --drop "<indices>"`
   (or `--drop-ids "<ids>"`); confirm the remaining count.

### 5. Reconcile taxonomy against your PER-USER memory (writes working/process_overrides.json)
This skill keeps a **per-user, durable taxonomy memory** so process / JTBD names stay stable across
runs instead of being re-invented each time — **Process is the aggregation anchor** (align-first,
create-if-novel; the standalone Job layer was dropped). **The memory is specific to the invoking
user and never shared:**
- The registry is `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json`, carrying an
  `owner` field. `<userkey>` is derived from the user's `mail` (from step 2); the file is on the
  user's own mount (syncs to their OneDrive Cowork folder).
- **First run = no memory.** There is NO bundled seed. `reconcile_taxonomy.py` also **ignores any
  registry whose `owner` isn't the invoking user** (a leaked/inherited/unstamped file), so a first
  run mints processes from the user's OWN sessions. Nothing user-specific ever ships in the folder.
- **Align:** `python /mnt/user-config/.claude/skills/cowork-dashboard-member/scripts/reconcile_taxonomy.py --in working/cowork_raw.json --owner "<signed-in user's mail>" --overrides working/process_overrides.json`
  For each **kept** session it (a) reuses a known **project**'s `{process, pillar, jtbd}`; else
  (b) aligns to an existing **process** by keyword similarity and registers a new project under it;
  else (c) mints a **new process** (flagged `"new"` — review/rename; on a first run every process is
  new, which is expected). It writes `working/process_overrides.json` and **persists the owner-stamped
  registry**. Run this **after** the privacy prune so excluded sessions never enter the registry.

`classify.py` then reads the overrides via `--overrides working/process_overrides.json`; without it,
it falls back to the bundled generic APQC taxonomy. `references/map-my-work-playbook.md` +
`value-pillars.md` document how to curate the registry / pillars.

### 6. Classify + compute (on the pruned set)
- `python /mnt/user-config/.claude/skills/cowork-dashboard-member/scripts/classify.py --in working/cowork_raw.json --out working/cowork_sessions.json --overrides working/process_overrides.json`
- `python /mnt/user-config/.claude/skills/cowork-dashboard-member/scripts/compute.py --in working/cowork_sessions.json --out working/cowork_roi_data.json`
- (If a credits ledger exists it is used automatically for the real-cost line; otherwise that line is omitted.)

### 7. Format the de-identified table message
```
python /mnt/user-config/.claude/skills/cowork-dashboard-member/scripts/format_member_message.py \
  --in working/cowork_roi_data.json --out working/member_message.html
```
The script prints the HTML body between `<<<COWORK-ROI-MEMBER-MESSAGE>>>` and `<<<END>>>` — use that
exact string as the message body. The header shows the period **and the runner's Role** (directory
`meta.role`; no country/name). Metric & section titles are kept **identical to the Copilot ROI Report
skill** (`cowork-roi-report/scripts/build_report.py`). The post is a sequence of **HTML `<table>`s**
(stable headers, one row per item) in this fixed order:
1. **Headline** — Metric · Value (Expert-equivalent hours +range, Professional-services value, Speed multiplier, Assisted hands-on hours, sessions, run tasks, deliverables, active days, hours/active day, real cost if measured).
2. **Where the time went — by task category** — Category · Band (low/typ/high) · Tasks · Hours · Value · % time.
3. **Business value pillars** — Pillar · Sessions · Hours · Value · % time.
4. **Jobs to be done** — Job to be done · Sessions · Hours · Value (de-duplicated `jtbd` from the durable registry via `reconcile_taxonomy.py`).
5. **Work by business process** — Process · Sessions · Hours · Value · % time (Process is the taxonomy anchor).
6. **Roles Cowork assembled for me** — Role · Hours · Value.
7. **Skills applied** — Skill · Deliverables · Sessions · Value.
8. **Analyzed → Produced** — Measure · Value, plus **Inputs by type** and **Outputs by type**.
9. **Deliverables & the skills behind them** — every deliverable made visible with a **de-identified descriptive label** (person/customer/raw-file names stripped — see §3) and **labelled with the business process it supported**: Deliverable · Type · Date · Business process · Skills · Hours · Value, followed by a **By type** rollup (Deliverable type · Count · Hours · Value · Skills used). The **By type** rollup is the shared-contract shape the aggregated Dashboard parses — do not remove its columns; the per-row **Deliverable** label column is member-post-only.
10. **Activity by day** — Date · Run tasks.

Every value comes from `cowork_roi_data.json`; no hand math.

### 8. Show + post
Show the user the rendered tables inline, then post to the channel resolved in **Target channel**
(reused from memory, or asked-for and parsed from the pasted link on first run):
`PostChannelMessage(team_id=<resolved team_id>, channel_id=<resolved channel_id>, subject="Cowork Dashboard — <window label>", body=<the HTML body>)`.
The platform shows its own approval dialog before anything sends.

### 9. Automate (only if the user chose it in step 1)
`SetupScheduledPrompt` (frequency **Week**, interval **2**, weekDays `["Monday"]`, hours `["8"]`, name
"Cowork Dashboard member (biweekly, Mondays)") — a fixed **every-other-Monday at 8 AM** cadence so every
member's 15-day window aligns regardless of install date — with a **self-contained** description:
> "Generate my Cowork Dashboard stats for the last 15 days: harvest my Cowork sessions, compute the
>  table-formatted de-identified post, then EMAIL me that it's ready and ask me to open this task's
>  chat to exclude any sessions I don't want shared before it posts to my team's Cowork report
>  channel. Do not post until I've reviewed."

**On each scheduled execution (no user present):** harvest → map-my-work → compute a draft, then
`SendEmailWithAttachments(to=[<user's own email>], subject="Your Cowork Dashboard post is ready to review",
body="<headline summary + the session inventory list>")` telling them to open **this task's chat** to
run the opt-out picker and post. **Never auto-post on a scheduled run** — the user always does the
final opt-out + post interactively in the task chat. Confirm setup in plain language.

## Guardrails
- **De-identified, not fully anonymized.** Never include any person's name, raw file names, prompt
  text, or **country**. The post DOES carry the runner's directory **Role** (job title — a
  de-identified attribute many people share), and the Jobs-to-be-done and business-process tables —
  including any **customer/account names** their text contains. Do not scrub customer names from
  process/JTBD strings.
- **Grouped business processes.** The "Work by business process" table shows a short canonical set
  (see `scripts/process_groups.json`); the underlying per-user registry and Jobs-to-be-done stay
  granular. This grouping + the skills vocabulary + the Role attribute are a **shared data contract** —
  they must match `cowork-roi-report`'s copies (the aggregated "Cowork report – ROI Advisors" reader
  reuses those). Change them in both bundles together.
- **Configured channel.** Post only to the team channel resolved in **Target channel** (from the
  bundled `config/team_channel.json` if a team default was baked in, else asked once from the pasted
  Teams link, then remembered). Never post to any channel the user didn't point the skill at, and
  never invent one. `config/team_channel.json` is the **only** team-configurable file — never ship the
  taxonomy registry or a populated `process_overrides.json`.
- **Conservative numbers.** All metrics come from the bundled pipeline — no hand math, no fabricated
  figures. If a section is empty, omit it rather than inventing.
- **Privacy opt-out is mandatory.** Always run step 4 before computing/posting. On interactive runs
  show the picker; on scheduled runs email the user to review in the task chat. Excluded sessions are
  dropped from `cowork_raw.json` so they are never classified, costed, named, or sent.
- **Scheduled runs never auto-post.** A scheduled execution emails the user and stops; posting only
  happens after the user's interactive opt-out. The platform approval dialog is the final gate.
- **Fixed biweekly cadence.** When automating, always schedule `SetupScheduledPrompt(frequency=Week,
  interval=2, weekDays=["Monday"], hours=["8"])` — every other Monday at 8 AM — so all members' 15-day
  windows align regardless of install date. The harvest window stays the **last 15 days**, and the
  review-email + opt-out flow is unchanged.
- **One post per run.** Re-running replaces the user's contribution; the manager skill keeps the latest per sender.
- **Per-user memory — never leak it.** The taxonomy registry is owner-scoped and owner-stamped;
  `reconcile_taxonomy.py` ignores any file that isn't the invoking user's, and a first run starts
  empty. NEVER bundle the registry, any `cowork-process-registry*.json`, or a populated
  `process_overrides.json` when packaging/sharing this skill — overrides ship as `{}` and are written
  under `working/` at runtime. (A prior version shipped a personal seed + populated overrides, which
  leaked one user's jobs/processes into everyone who ran the package — that is the fatal flaw this
  guard prevents.)

## Bundled files (self-contained)
- `config/team_channel.json` — per-team channel default (ships **empty**; filled per-team by the installer generator so members skip the first-run link prompt — see **Target channel** step 0). Never commit a populated copy.
- `scripts/prune_sessions.py` — lists the session inventory + applies the privacy opt-out.
- `scripts/format_member_message.py` — renders `cowork_roi_data.json` into the de-identified HTML table post.
- `scripts/reconcile_taxonomy.py` — aligns each kept session to the invoking user's **owner-scoped** registry (align-first, create-if-novel; ignores any file that isn't theirs); writes `working/process_overrides.json` + persists the owner-stamped registry. Takes `--owner`. Reuses `classify.py`'s matcher.
- `scripts/classify.py` — ext→category classifier; applies per-run overrides via `--overrides working/process_overrides.json`, then groups the process label via `process_groups.json`. Reads `apqc_taxonomy.json`, `roles_taxonomy.json`, `process_groups.json`.
- `scripts/compute.py` — research-anchored two-clock model → `cowork_roi_data.json` (incl. `pct_time`).
- `scripts/apqc_taxonomy.json`, `scripts/roles_taxonomy.json`, `scripts/skills_vocabulary.json` — taxonomy/vocabulary data (`skills_vocabulary.json` is the curated ~30-skill canonical set).
- `scripts/process_groups.json` — canonical business-process **grouping** map (APQC labels + registry/override names → one short set); applied by `classify.py`. Shared with `cowork-roi-report`.
- `scripts/process_overrides.json` (ships empty `{}`, vestigial) + `scripts/process_overrides.example.json` (format example). The real per-run overrides live at `working/process_overrides.json` — never in the bundle.
- **No seed ships.** The per-user registry lives at `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json` (owner-stamped) and is created on first run from the user's own sessions.
- `references/map-my-work-playbook.md`, `references/value-pillars.md` — how to curate the registry / value pillars.

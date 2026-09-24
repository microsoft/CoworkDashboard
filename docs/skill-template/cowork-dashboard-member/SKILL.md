---
name: cowork-dashboard-member
description: |
  Member step of the Cowork Team Report: gathers the user's own Cowork sessions, supports exclusions, computes impact metrics, and emails aggregate tables to a configured Teams channel email address. Excludes person names and prompts and replaces raw file names with de-identified descriptive labels; retains customer/account names. Supports one-time or biweekly runs with review before sending.
  Use for "send my Cowork Team Report stats", "email my Cowork stats to the team channel", "run the Cowork Team Report member step", or "share my Cowork impact with the team".
  Do NOT use for the full personal HTML report (use cowork-roi-report), the manager-side team dashboard, GitHub Copilot reports, or single-meeting summaries.
metadata:
  category: productivity
  icon: PeopleTeam
  version: "27"
---

# Cowork Team Report — Member step (de-identified table email to the team channel)

Produces the **per-person, de-identified** input to a team Cowork Team Report, rendered as
**HTML tables** so it's both readable in the Teams channel email and easy for a downstream Cowork task to parse.
**No person names or prompts leave the machine, and raw file names are replaced with de-identified
descriptive labels** — the email carries aggregate totals,
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
- "Email my Cowork Team Report stats to the team channel" / "run the Cowork Team Report member step"
- A team cadence (e.g. every other Monday) where each member contributes their stats.

## When NOT to use
- Full personal HTML report with project detail → `cowork-roi-report`.
- Gathering everyone's reports into the team dashboard → the manager skill.

## Target channel email — configured in the bundle
This skill sends to **one Teams channel email address that your team's admin / manager / lead
configured** for Cowork reports (channel named e.g. `Cowork report - <team>`).

1. Read `config/team_channel.json` in this skill's folder.
2. Require a non-empty, syntactically valid `channel_email`.
3. Send the HTML report to that address with
   `SendEmailWithAttachments(to=[channel_email], subject=..., body=<html>)`.

The generic bundle ships with an empty `channel_email`; the installer generator fills it for each
team. **Never invent, infer, or ask the member to choose a recipient.** If `channel_email` is empty
or invalid, stop and tell the user that their admin/manager/lead must reinstall a team-configured
copy or populate the channel email in the config. Do not fall back to `PostChannelMessage`.

All script paths below are under this skill's own folder:
`/mnt/user-config/skills/cowork-dashboard-member/scripts/`.

## Workflow

### 0. Welcome the user (inviting on first run, short preview after)
**First run (the user hasn't run this before):** open with a warm,
plain-language welcome — what this is, why it helps, the privacy promise, and the 1-2-3 — before doing
anything. Name the team from `config/team_channel.json` `channel_name` when it's set. Keep it friendly
and brief, e.g.:
> 👋 **Welcome!** This shares your **Copilot Cowork** impact with your team's private report channel so
> everyone's wins add up — while keeping your details private.
> **Your privacy:** no names or prompts leave your machine, and raw file names are replaced with
> de-identified descriptions; you review every session and can exclude any of it before anything sends.
> Only de-identified stats are shared.
> **Here's the 1-2-3:**
> 1. I **look at your Cowork sessions and classify them** (work, time, deliverables).
> 2. **You review and can delete any sessions** before anything leaves your machine.
> 3. The confirmed sessions are **emailed — de-identified — to your team's private Teams channel**, so
>    your manager can roll them into an aggregate report.

**Later runs:** just show the short 3-line preview (the numbered 1-2-3 above) so the user knows the
flow without the full intro. Then continue with the steps below.

### 1. Choose run mode + period
Ask once with **`AskUserQuestion`**: *"Run this once, or automate it every other Monday?"* — options
**"Just once"** / **"Automate biweekly on Mondays (email me to review before each send)"**. The period
defaults to the **last 15 days** (ask only if the user names a different window). Window = N days
ago 00:00 → today 23:59, local time. If they choose automate, still produce a report now **and** set
up the schedule in step 9.

> **Note:** This automate/schedule prompt appears on the **first RUN** of the skill, not at install.

### 2. Resolve identity & dates
`GetMyDetails(select="mail,userPrincipalName,displayName,jobTitle")` (the `mail` is the per-user memory
owner — passed to `reconcile_taxonomy.py --owner` in step 5; `jobTitle` becomes the runner's **Role**
attribute shown in the email — see step 3). compute `after` = N days ago 00:00 local, `before` =
today 23:59 local, `window.label` = "Last N days", `window.months` = N/30.
**Role, not identity:** carry the directory `jobTitle` only. Never add country, and never any person
name, file name, or prompt.

### 3. Harvest the user's Cowork sessions (self-contained)
**First-run telemetry hook check:** read `/mnt/user-config/settings.json`; if it is missing or lacks a
Stop hook pointing to an existing `mine_session.py`, tell the user **the forward-capture hook is not
active**. Installed scripts alone do not enable capture; do not silently repair or activate hooks.

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
  This `name` is shown verbatim in the **Deliverable** column of the emailed table (§7.9), so it must
  carry NO personal or customer identifier and NO raw filename. (Keep the real `ext` — it drives
  classification.)
- **Live-session telemetry (captures folder-less sessions).** Run
  `python .../scripts/mine_session.py --out working/session_telemetry.json --log /mnt/user-config/.claude/cowork-session-telemetry.json`
  to record the live session's `exec_min`, tool intensity, artifacts, and per-category `runs`
  (Outlook-mail → `email`, Teams → `comms`, transcript/calendar → `meeting`, code → `code`,
  research → `analysis`). **Merge into `sessions` any telemetry id NOT covered by a Cowork folder**
  (`has_folder:false`, `outputs:[]`), carrying its `runs` and `exec_min`. This is what stops
  artifact-free **email / Teams / meeting triage** sessions — which write no output file — from
  dropping out of the artifact-based harvest. Forward-only; prefer telemetry `exec_min` where both exist.
- Write `working/cowork_raw.json`:
  ```json
  { "meta": {"user":"<name>","email":"<mail>","role":"<jobTitle from step 2>","generated":"<YYYY-MM-DD>",
             "window":{"from":"...","to":"...","label":"Last N days","months":0.5},"hourly_rate":72},
    "sessions": [ {"id":"<slug>","date":"YYYY-MM-DD","hour":12,"goal":"<short verb-first phrase>",
                   "inputs":[{"name":"report.pdf","ext":"pdf"}],
                   "outputs":[{"name":"AI-in-One insights deck","ext":"pptx","skills":["Presentation Design"]}],
                   "skills":["Data Analysis"], "professional_roles":["Data Analyst"],
                   "has_folder":true, "exec_min":null},
                  {"id":"<telemetry-8char>","date":"YYYY-MM-DD","hour":9,"goal":"triage and prioritize inbox",
                   "inputs":[],"outputs":[],"has_folder":false,"runs":{"email":2},"exec_min":8.0,
                   "request":"triage and prioritize inbox","actions":["mcp__outlook__ListMessages","mcp__outlook__MarkRead"],
                   "apps_accessed":["Outlook"],"sources_reviewed":0} ] }
  ```
  (`runs` is carried straight through by `classify.py` and consumed by `compute.py`; a folder-less
  session with no `runs` and no category signals still classifies as `general`.)
  **Evidence fields** (`request` / `actions` / `apps_accessed` / `sources_reviewed`) come from the
  transcript action trace (`mine_session.py`) and let `compute.py` grade Cowork-fit from *what the
  session actually touched*. Grading follows an evidence-first hierarchy: **≥2 apps in play**
  (trace-verified ∪ inferred from outputs/goal), **code/build**, **automation/workflow** (triage,
  scan, sweep, connector, recurring run — *never* graded below High), **multi-document synthesis**
  (≥3 docs across ≥2 formats, or >5 sources), or **≥2 output formats** ⇒ **High**; a single surface
  with ≥2 input formats / ≥3 files / a light platform op ⇒ **Moderate**; a purely conversational or
  lone-app task ⇒ **Low**. Emit the evidence fields **only when a transcript was parsed**. Their
  *absence* no longer forces a downgrade — **Ungraded (insufficient evidence)** is now reserved for
  the rare case of a saved output of an *unrecognized* type with no code/automation/multi-format/
  cross-app signal **and** no trace; a missing trace alone never forces it. Never fabricate the fields
  as `[]` for a folder-only session that had no trace — ABSENT and `[]` mean different things to the
  grader.
### 3b. Backfill chat-only sessions (no folder)
**Historical coverage is separate from forward capture.** OneDrive holds only file artifacts, not
the history of chats that saved no files. The telemetry log is **forward-only**: repairing the hook
or parsing the live transcript cannot recover past chat-only sessions. The only known recovery
source is the **Cowork web app's session list**.

1. If browser automation is available, ask the user **once per run**, with **`AskUserQuestion`**:
   *"Backfill chat-only sessions from the Cowork web app? I'll read only session titles and dates,
   never chat contents or prompts."* Offer **Yes** / **No**. Proceed only on Yes; an unattended run
   must defer this choice to the interactive review rather than assume consent.
2. On Yes, open the Cowork web app directly at **`https://aka.ms/cowork`** — this is the canonical
   entry point; **navigate there yourself and do NOT ask the user for the web address**. Enumerate the
   **left-nav session list** within the selected window, scrolling/loading the list as needed. Collect
   **title + date only — never open conversations, read chat contents or prompts, or inspect `/cost`**.
   If sign-in is needed, let the user complete it in the browser; do not request credentials in chat.
   Only if `https://aka.ms/cowork` fails to resolve to the signed-in session list (e.g. the redirect
   changed or the tenant uses a different host) ask the user **once** for their Cowork web address as a
   fallback.
3. Match against the folder inventory and telemetry ids already collected, using existing id
   mappings or an unambiguous title/date match. Add only unmatched sessions to `working/cowork_raw.json`:
   ```json
   {"id":"<slugified title+date>","date":"YYYY-MM-DD","hour":null,
    "goal":"<title as a short verb-first phrase>","inputs":[],"outputs":[],
    "has_folder":false,"backfilled":true}
   ```
   Slugify title plus the displayed date deterministically (lowercase, spaces/punctuation to
   hyphens). Rephrase the title only; do not invent work. Do not guess hidden dates/times or merge
   ambiguous same-title/same-date sessions: flag that uncertainty in the coverage note. Add **no
   `request`, `actions`, `apps_accessed`, or `sources_reviewed` evidence fields** — those exist only
   when a transcript was parsed. Do not invent measured `exec_min` or tool-derived `runs`.
4. These backfilled sessions go through the **same mandatory §4 privacy picker before anything is
   classified or computed**; excluding one removes it entirely from the pending report.
5. If the browser is unavailable, access fails, the list is incomplete, or the user declines, say
   so plainly. **Report the historical chat-only coverage gap in the report preview**, without
   guessing the missing sessions, their work, or their metrics.

Do **not** classify/compute yet — the user prunes first.

### 4. Privacy opt-out — let the user remove any chat/task BEFORE anything is computed
**Mandatory, every run, before classify/compute.** Nothing about an excluded session is ever
classified, costed, named, or sent.
1. List the inventory: `python .../scripts/prune_sessions.py --in working/cowork_raw.json --list`
   (one numbered line per session between `<<<COWORK-SESSION-INVENTORY>>>` markers, **plus a
   ready-to-use options array between `<<<COWORK-SESSION-PICKER-JSON>>>` markers** — one object per
   session: `{index, id, label, desc}`, where `label` is the `Exclude — <name>` checkbox title and
   `desc` is the date/deliverable detail. The array holds **only sessions** — no navigation or
   include-all entries).
2. **Interactive run — a real multi-select checkbox picker, NEVER a free-text prompt.** Use a
   **two-stage** design so the common "keep everything" case is ONE click and no one ever has to type
   "include all" or hit Skip to advance.

   **Stage 1 — the include-all gate (always ask this first, single question).** Ask ONE
   `AskUserQuestion` (not multiSelect): *"Ready to share your Cowork stats. Include all N sessions, or
   exclude specific sessions first?"* with two options:
   - **"✅ Include all N sessions (nothing to exclude)"** — the default/first option.
   - **"Exclude specific sessions"**.
   Include the short **privacy reminder** (exclude anything personal or non-work you're not comfortable
   sharing — each session's deliverables go out with it). If the user picks **Include all**, exclude
   nothing and continue immediately — **do NOT page through anything**. Only if they pick **Exclude
   specific sessions** go to Stage 2.

   **Stage 2 — the per-session exclude picker (only when the user chose "Exclude specific sessions").**
   Ask with an **`AskUserQuestion` card using `multiSelect: true`**. The card's options are **ONLY the
   per-session "Exclude — <name>" checkboxes** from the picker-JSON (`label` = the checkbox title,
   `desc` = the date/deliverable detail, value = its `id`). Ticking an option **excludes** that session.
   - **Do NOT add ANY non-session options.** No "Include all / include remaining / stop reviewing", no
     "Keep all of these", and **no in-list "Next — review more sessions" / "Done" option**. The list is
     nothing but `Exclude — <session>` rows. (The earlier include-all/next-in-list options were the
     defect — remove them.)
   - **Navigation is the card's OWN button below, not a list option.** Paginate by putting each page of
     sessions as a **separate `multiSelect` question inside the SAME `AskUserQuestion` call** — the host
     then shows **Next** to move between pages and shows the **Submit** button **only on the final
     page**. Selecting checkboxes on a non-final page must NOT turn its button into Submit; it stays
     **Next**. **Never use Skip** — there is no Skip in this flow.
   - Each page/question is titled e.g. *"Select sessions to EXCLUDE (page X of Y)"* with the short
     **privacy reminder**. Put ≤4 sessions per question (all four option slots are sessions now — no
     slot is spent on navigation). A single `AskUserQuestion` call holds up to 4 questions × 4 options
     (16 sessions); if there are more, continue in a follow-up call — but only the **very last page of
     the last call** shows Submit; every earlier page shows Next.
   - **DO NOT** paste the session list into the question text, number them in prose, or ask the user to
     "reply with session numbers / type which to exclude". Every session is an individually tickable
     `Exclude — <name>` checkbox; advancing is the card's Next button; finishing is the final Submit.
3. **Scheduled run (no interactive user):** do **not** show the picker (it would hang). Compute the
   draft and **email the user to review/exclude in the task chat** (see step 9) — never send without
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
exact string as the email body. The header shows the period **and the runner's Role** (directory
`meta.role`; no country/name). Metric & section titles are kept **identical to the Copilot ROI Report
skill** (`cowork-roi-report/scripts/build_report.py`). The email is a sequence of **HTML `<table>`s**
(stable headers, one row per item) in this fixed order:
1. **Headline** — Metric · Value (Expert-equivalent hours +range, Professional-services value, Speed multiplier, Assisted hands-on hours, sessions, run tasks, deliverables, active days, hours/active day, real cost if measured).
2. **Where the time went — by task category** — Category · Band (low/typ/high) · Tasks · Hours · Value · % time.
3. **Business value pillars** — Pillar · Sessions · Hours · Value · % time.
4. **Jobs to be done** — Job to be done · Sessions · Hours · Value (de-duplicated `jtbd` from the durable registry via `reconcile_taxonomy.py`).
5. **Work by business process** — Process · Sessions · Hours · Value · % time (Process is the taxonomy anchor).
6. **Roles Cowork assembled for me** — Role · Hours · Value.
7. **Skills applied** — Skill · Deliverables · Sessions · Value.
8. **Analyzed → Produced** — Measure · Value, plus **Inputs by type** and **Outputs by type**.
9. **Deliverables & the skills behind them** — every deliverable made visible with a **de-identified descriptive label** (person/customer/raw-file names stripped — see §3) and **labelled with the business process it supported**: Deliverable · Type · Date · Business process · Skills · Hours · Value, followed by a **By type** rollup (Deliverable type · Count · Hours · Value · Skills used). The **By type** rollup is the shared-contract shape the aggregated Dashboard parses — do not remove its columns; the per-row **Deliverable** label column is member-email-only.
10. **Activity by day** — Date · Run tasks.

Every value comes from `cowork_roi_data.json`; no hand math.

### 8. Show + email
Show the user the rendered tables inline, then read `channel_email` from
`config/team_channel.json` and send:
`SendEmailWithAttachments(to=[<configured channel_email>], subject="Cowork Team Report — <window label>", body=<the HTML body>)`.
Use the HTML body exactly as rendered and do not attach the raw working files. The platform shows
its own approval dialog before anything sends. Never use `PostChannelMessage`.

### 9. Automate (only if the user chose it in step 1)
`SetupScheduledPrompt` (frequency **Week**, interval **2**, weekDays `["Monday"]`, hours `["8"]`, name
"Cowork Team Report member (biweekly, Mondays)") — a fixed **every-other-Monday at 8 AM** cadence so every
member's 15-day window aligns regardless of install date — with a **self-contained** description:
> "Generate my Cowork Team Report stats for the last 15 days: harvest my Cowork sessions, compute the
>  table-formatted de-identified email, then EMAIL me that it's ready and ask me to open this task's
>  chat to exclude any sessions I don't want shared before it is emailed to my team's Cowork report
>  channel. Do not send the report until I've reviewed."

**On each scheduled execution (no user present):** harvest → map-my-work → compute a draft, then
`SendEmailWithAttachments(to=[<user's own email>], subject="Your Cowork Team Report is ready to review",
body="<headline summary + the session inventory list>")` telling them to open **this task's chat** to
run the opt-out picker and send. **Never auto-send the report on a scheduled run** — the user always
does the final opt-out + channel-email send interactively in the task chat. Confirm setup in plain language.

## Guardrails
- **De-identified, not fully anonymized.** Never include any person's name, raw file names, prompt
  text, or **country**. The email DOES carry the runner's directory **Role** (job title — a
  de-identified attribute many people share), and the Jobs-to-be-done and business-process tables —
  including any **customer/account names** their text contains. Do not scrub customer names from
  process/JTBD strings.
- **Grouped business processes.** The "Work by business process" table shows a short canonical set
  (see `scripts/process_groups.json`); the underlying per-user registry and Jobs-to-be-done stay
  granular. This grouping + the skills vocabulary + the Role attribute are a **shared data contract** —
  they must match `cowork-roi-report`'s copies (the aggregated "Cowork report – ROI Advisors" reader
  reuses those). Change them in both bundles together.
- **Configured channel email.** Send the report only to the `channel_email` in the bundled
  `config/team_channel.json`. Never ask the member to choose a recipient, never invent one, and
  never fall back to a Teams API post. `config/team_channel.json` is the **only** team-configurable
  file — never ship the taxonomy registry or a populated `process_overrides.json`.
- **Conservative numbers.** All metrics come from the bundled pipeline — no hand math, no fabricated
  figures. If a section is empty, omit it rather than inventing.
- **Privacy opt-out is mandatory.** Always run step 4 before computing/sending. On interactive runs
  show the picker; on scheduled runs email the user to review in the task chat. Excluded sessions are
  dropped from `cowork_raw.json` so they are never classified, costed, named, or sent.
- **Scheduled runs never auto-send the report.** A scheduled execution emails the user and stops;
  delivery to the channel email only happens after the user's interactive opt-out. The platform
  approval dialog is the final gate.
- **Fixed biweekly cadence.** When automating, always schedule `SetupScheduledPrompt(frequency=Week,
  interval=2, weekDays=["Monday"], hours=["8"])` — every other Monday at 8 AM — so all members' 15-day
  windows align regardless of install date. The harvest window stays the **last 15 days**, and the
  review-email + opt-out flow is unchanged.
- **One report email per run.** The manager skill should keep the latest contribution per sender.
- **Per-user memory — never leak it.** The taxonomy registry is owner-scoped and owner-stamped;
  `reconcile_taxonomy.py` ignores any file that isn't the invoking user's, and a first run starts
  empty. NEVER bundle the registry, any `cowork-process-registry*.json`, or a populated
  `process_overrides.json` when packaging/sharing this skill — overrides ship as `{}` and are written
  under `working/` at runtime. (A prior version shipped a personal seed + populated overrides, which
  leaked one user's jobs/processes into everyone who ran the package — that is the fatal flaw this
  guard prevents.)

## Bundled files (self-contained)
- `config/team_channel.json` — per-team Teams channel email target (ships with an empty
  `channel_email`; filled per-team by the installer generator). Never commit a populated copy.
- `scripts/prune_sessions.py` — lists the session inventory + applies the privacy opt-out.
- `scripts/mine_session.py` — live-session telemetry hook: mines the current transcript for real `exec_min`, tool intensity, artifacts, and per-category `runs` (Outlook-mail→email, Teams→comms, transcript/calendar→meeting, code→code, research→analysis); upserts a durable log so folder-less email/Teams/meeting triage sessions are still harvested.
- `scripts/format_member_message.py` — renders `cowork_roi_data.json` into the de-identified HTML table email.
- `scripts/reconcile_taxonomy.py` — aligns each kept session to the invoking user's **owner-scoped** registry (align-first, create-if-novel; ignores any file that isn't theirs); writes `working/process_overrides.json` + persists the owner-stamped registry. Takes `--owner`. Reuses `classify.py`'s matcher.
- `scripts/classify.py` — ext→category classifier; applies per-run overrides via `--overrides working/process_overrides.json`, then groups the process label via `process_groups.json`. Reads `apqc_taxonomy.json`, `roles_taxonomy.json`, `process_groups.json`.
- `scripts/compute.py` — research-anchored two-clock model → `cowork_roi_data.json` (incl. `pct_time`).
- `scripts/apqc_taxonomy.json`, `scripts/roles_taxonomy.json`, `scripts/skills_vocabulary.json` — taxonomy/vocabulary data (`skills_vocabulary.json` is the curated ~30-skill canonical set).
- `scripts/process_groups.json` — canonical business-process **grouping** map (APQC labels + registry/override names → one short set); applied by `classify.py`. Shared with `cowork-roi-report`.
- `scripts/process_overrides.json` (ships empty `{}`, vestigial) + `scripts/process_overrides.example.json` (format example). The real per-run overrides live at `working/process_overrides.json` — never in the bundle.
- **No seed ships.** The per-user registry lives at `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json` (owner-stamped) and is created on first run from the user's own sessions.
- `references/map-my-work-playbook.md`, `references/value-pillars.md` — how to curate the registry / value pillars.

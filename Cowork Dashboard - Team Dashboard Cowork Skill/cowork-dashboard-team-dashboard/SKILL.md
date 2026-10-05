---
name: cowork-dashboard-team-dashboard
description: |
  Manager-side team rollup for Copilot Cowork ROI. Aggregates the de-identified stats teammates email to a shared Teams channel into a private, locally served dashboard with four tabs and a built-in guide. Share only a reviewed Markdown or PDF export after explicit confirmation, never the local URL or standalone HTML. First run remembers the Teams channel link; each run reads the latest 15 days and keeps the latest report per person. The public site contains no member records and shows a
  breakdown only when at least 3 contributors support it. Small homogeneous teams; not org-wide.
  Use when the user asks to "build the team Cowork Team Report", "aggregate my team's Cowork stats", "roll up the channel posts", "manager Cowork Team Report", "email the team dashboard", to "walk me through setup" / "set up the skill" right after installing it, or to "send / share the member skill with my team" / "invite my team" / set up / refresh the rollup.
  Do NOT use for: the personal report (cowork-roi-report), a member's own post (cowork-dashboard-member), the member-side aggregated post (cowork-roi-report-aggregated), org-wide/large-team aggregation, GitHub Copilot reports, or single-meeting summaries.
cowork:
  category: analysis
  icon: BarChart4
---

# Cowork Team Report — Team Dashboard (manager rollup)

Aggregates the **de-identified Cowork Team Report messages** teammates email (via the **Copilot ROI
Member** skill, `cowork-dashboard-member`) to a shared Teams channel and renders an aggregate-only
**local website**, served on `http://127.0.0.1:7333/`. HTML, CSS, JavaScript and public JSON are
separate local files, with no CDN or external assets. The guide remains inside the dashboard.
The site is not published, and its localhost URL is not a share link. Share a reviewed Markdown
summary or a PDF saved with the dashboard's print control only after explicit confirmation.

Local describes the site, not the agent's data path: host tools still access Teams and the model
may process those results. Keep raw messages and private working JSON outside the served folder.
Do not collect mailbox/transcript history, add startup integration, or create schedules without
an explicit request. This adaptation does not certify antivirus clearance.

**This skill only reads what the Member skill emails into the channel.** It never harvests anyone's OneDrive and
never sees names, files, or prompts. If a label (business process, skill, Role) doesn't match the
Member bundle's copy, aggregation drifts — the taxonomy files here are **byte-for-byte mirrors** of
the Member skill's (see *Cross-skill contract*).

## Scope (v1)
- **Small, homogeneous teams** (people doing similar work), **team level**. A handful of
  contributors sharing one channel.
- **Not** org-wide / large-team / multi-channel aggregation, and **not** cross-team benchmarking.

## When NOT to Use
- **A single person's full impact report** → `cowork-roi-report` (rich personal web app).
- **Emailing your own de-identified stats** to the channel → `cowork-dashboard-member`.
- **The member-side anonymized table post** → `cowork-roi-report-aggregated`.
- **Org-wide / multi-team / cross-channel aggregation** — out of scope for v1; don't force it.
- **GitHub Copilot / IDE usage reports**, **daily briefings**, or **single-meeting summaries** —
  different skills entirely.
- If the shared channel has **no Cowork Team Report posts in the last 15 days**, don't fabricate a dashboard —
  say the window was empty and offer to widen it.

## First run — point the skill at the channel (once)

The rollup reads ONE shared Teams channel that teammates email reports to. The channel is **not hard-coded**.

> **If the manager just installed the skill and asked to "walk me through setup" (or this is the first
> setup turn), do the 1:1 share step FIRST** — see *Right after install — offer to send the member
> skill to teammates 1:1* below — **before** asking for the channel link. Installing the manager skill
> alone does nothing: unless teammates get the member skill, the channel stays empty and every run
> produces a blank dashboard. Lead with getting the member skill into their hands, then set up the
> channel.

1. **Load `config/team_config.json`.** If `team_id` **and** `channel_id` are already filled in — the
   normal case for a zip downloaded from the **Installer page**, which bakes your channel into the
   config — **the channel is already set up. Do NOT ask for a channel link: skip steps 2–3 entirely**
   and go straight to the invite / 1:1 share and the workflow. Only treat this as a blank first run (and
   do steps 2–3) when **both** fields are empty, which happens only for a hand-built zip.
2. **Only if the channel is blank — ask for the link.** Use `AskUserQuestion` to ask the user to paste
   the **link of the Teams channel** where the team emails its Cowork Team Report stats (in Teams: channel ⋯ → *Get link to
   channel*). This must be the same channel whose email address is configured in `cowork-dashboard-member`.
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

### First run also — invite the team (so no one gets a bare .zip)
Right after the channel is resolved on a **first run** (and any time the manager asks to "invite the
team" / "onboard members"), **onboard members in-place instead of leaving the manager to hand-deliver
a zip.** Members are already in this channel, so an inviting welcome posted here *is* the delivery.
1. **Get the member skill to share (link or attached ZIP).** Read `member_download_url` from
   `config/team_config.json`. If blank, check whether the member `.zip` is already attached to this
   session; if not, offer clear choices with `AskUserQuestion` — **Attach the member ZIP** (click the
   **+** icon in Copilot Cowork and upload `cowork-dashboard-member.zip`, which you can then post into
   the channel), **Paste a download link** (saved back to the config), or **Skip** (proceed without one —
   the invite tells members to use the link the manager shares). Never make the link mandatory.
2. **Render the invite:**
   ```
   python scripts/make_invite.py --team-name "<team_name>" \
       --download-url "<member_download_url>" --cadence "every other Monday" --out-dir working
   ```
   It prints an inviting **channel post** (HTML), an **email** subject+body, and a **plaintext** blurb
   between stable markers — each explains what the skill is, why it helps, the privacy promise, and the
   1-2-3 to get started, with the download link baked in.
3. **Post it to the channel and pin it.** **Print the full rendered post for the manager to read first**
   (not just "here's the draft"), get an OK, then
   `PostChannelMessage(team_id, channel_id, body=<the CHANNEL-POST html>)`; suggest they **pin** the
   message so newcomers always see how to join. This reaches every member without any manual sending.
4. **Optionally email it too.** If the manager wants a nudge beyond the channel, email the channel
   members the invite body (same recipients rule as workflow step 6) — no attachment needed.
Do this **once**; on later runs skip it unless the manager explicitly asks to re-invite.

### Right after install — offer to send the member skill to teammates 1:1 (do this first)
**On the manager's very first setup turn — right after the skill is installed, before pointing at the
channel — proactively offer to deliver the member skill to specific people 1:1**, so the manager
doesn't have to chase anyone down. (Skills run no code at install, so this first interaction after
install is the earliest possible moment.) This does **not** require the channel to be set up first,
and it is separate from actually running a report; it's in addition to the in-channel welcome.
1. **Ask if they want to.** With `AskUserQuestion`: *"Want me to send the member skill to specific
   teammates now, one-to-one?"* — options **Yes** / **Not now**. On "Not now", stop (the pinned
   channel welcome already reaches everyone in the channel); mention they can say "invite members"
   anytime.
2. **Gather recipients** — ask how (`AskUserQuestion`):
   - **Type email addresses** — the manager pastes addresses (comma / space / newline separated); or
   - **Pick from the channel** — list the current channel members (host Teams member-list tool, e.g.
     `ListChannelMembers`) and let the manager multi-select; **always include an "Include everyone in
     the channel" choice at the top** that selects **all** members at once. When they pick it, page
     through `ListChannelMembers` yourself (follow `next_link` until exhausted) to build the full roster
     — the manager should **not** have to scroll or click through a paginated picker. Confirm the total
     count (e.g. "Send to all 12 members?") before proceeding.
3. **Resolve & validate.** Look each address up in the directory (e.g. `GetMultipleUsersDetails`) to
   get first/display names and confirm it's a real, mailable user. Drop and report any that don't
   resolve; **never invent addresses**.
4. **Make sure the member skill is available to send — and offer an explicit "attach the ZIP" option.**
   First check whether the member `.zip` (`cowork-dashboard-member.zip`) is **already attached to this
   session** — the manager may have uploaded it alongside the manager zip. If it is, use that file and
   move on. If it's **not** attached, **don't drop a bare "type your answer" box on the manager** — use
   `AskUserQuestion` with two clear choices:
   - **Attach the member ZIP** — the default; tell them to click the **+** icon in Copilot Cowork and
     upload `cowork-dashboard-member.zip` (the one they downloaded from the Installer page), then continue;
   - **Skip for now** — proceed without 1:1 delivery (the pinned channel welcome still reaches everyone).
   The attached `.zip` is all you need to send — don't ask for a download link here.
5. **Render the message per recipient.** Run `make_invite.py` with `--recipient-name "<first name>"`;
   it prints every variant between stable markers. Take the one matching how you'll deliver:
   - **Teams DM:** the body between `<<<MEMBER-INVITE-DM>>>` / `<<<END-DM>>>`.
   - **Email:** the subject between `<<<MEMBER-INVITE-EMAIL-SUBJECT>>>` / `<<<END-EMAIL-SUBJECT>>>` and
     the body between `<<<MEMBER-INVITE-EMAIL-BODY>>>` / `<<<END-EMAIL-BODY>>>`, with the member `.zip` attached.
   ```
   python scripts/make_invite.py --team-name "<team_name>" \
       --download-url "<member_download_url>" --cadence "<cadence>" \
       --recipient-name "<first name>" --out-dir working
   ```
6. **Preview the exact message, then confirm (always).** Before sending anything, **render each message
   and print it in full in the chat so the manager reads exactly what will go out** — never ask for
   approval with only a description, a filename, or "shown above". Display:
   - the **final recipient list**;
   - for **email** delivery: the **subject line** and the **full email body**, and name the attachment
     (`cowork-dashboard-member.zip`);
   - for **Teams DM** delivery: the **full DM body** (show one fully rendered example and note each is
     personalized by first name).
   Only after showing that, ask for explicit confirmation with `AskUserQuestion`
   (**Send now** / **Edit list** / **Cancel**). Send nothing until they approve.
7. **Send 1:1.** On approval, direct-message each recipient with the host's 1:1 Teams chat tool (e.g.
   `SendChatMessage` / `SendMessageToUser` / `SendFileToUser`, addressed by email), body = that person's
   rendered DM, and **attach the member `.zip`** the manager downloaded so install is one click. If no
   file-to-chat tool is available, include the download link in the message instead.
8. **Report results.** Tell the manager who was messaged and list any failures. For a failure, offer a
   fallback: email that person the same invite (`SendEmailWithAttachments`) or hand them the link.
9. Do this **once**; on later runs skip unless the manager asks to "send the member skill to
   <people>" / "invite <names>".

**Never message anyone the manager didn't list or pick, and never send without the review-and-confirm
in step 6.**

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
  the **latest post per sender** (sender IDs are used transiently and never written), numbering
  contributors only inside the private working file;
- reads each post's parser-stable tables by header signature (tolerant of metric wording drift);
- parses the **Role** line and report metrics into a private working file; this file is not a
  deliverable and must never be emailed, published, or attached;
- **groups business processes** (`process_groups.json`) and **canonicalizes skills**
  (`skills_vocabulary.json` + `skill_aliases.json`);
- writes `working/team_data.json` (meta + snapshots + per-contributor metrics for internal aggregation).

The private working JSON is not the public data contract. `build_dashboard.py` must first construct
the separate public aggregate payload: omit contributor records and contributor links, and include
each category, process, role, skill, deliverable format, fit grade, and secondary breakdown only when
at least `privacy_k_threshold` distinct contributors support it. Combine small residual role groups
only when the pooled group also reaches the threshold; otherwise suppress them. Do not publish named
deliverables, individual task rows, task descriptions, per-item dates, or individual role assignments.
Keep the aggregate charts and controls, but never weaken the cohort checks to fill sparse charts.

### 4. Build the dashboard with the bundled renderer (guide built in)
```
python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
```
**Always use this bundled build path. Never hand-author, simplify, replace, or summarize the
dashboard layout.** `build_outputs.py` invokes `build_dashboard.py` and then the mandatory
`verify_dashboard.py` structural gate. A failed build or verification is not a usable deliverable.

Renders `output/team-dashboard/`:
- **`index.html`**, **`assets/dashboard.css`**, **`assets/dashboard.js`**,
  **`dashboard-data.json`**, **`dashboard-glossary.json`**, and **`team-summary.md`**.
  No inline scripts or embedded data; all assets are local. Four small
  tabs: **Overview** (auto-insights + KPI band) · **Impact & Value** (categories with $ and
  thresholded contributor reach, roles, deliverables by format) · **How Cowork is used**
  (business-process accordion — each process expands to thresholded format and skill aggregates,
  plus the Cowork-fit waterfall and category mix) ·
  **How to read** (the full in-dashboard guide:
  every KPI, the four tabs, the controls, how task categories are derived, the privacy model, and
  the methodology). Every section title also carries a clickable **"?"** popover. Value = hours ×
  rate, recomputed live by a rate control.

The **How to read** tab remains inside the local dashboard. `build_outputs.py` just drives
`build_dashboard.py` (still runnable on its own). The legacy PDF (`build_guide_pdf.py`) is retained
but **off by default**; pass `--with-pdf` to `build_outputs.py` only if someone explicitly wants a
printable copy.

### 5. Verify the rendered dashboard — mandatory delivery gate
First run the bundled structural verifier explicitly (the build already runs it once):
```
python scripts/verify_dashboard.py --in output/team-dashboard/index.html
```
It must confirm all **four tabs**, separate local assets, cohort-filtered public JSON, controls, and every required
aggregate visual:
- Cowork-fit **waterfall**.
- **Category bars**.
- **Stacked category mix**.
- Expandable **business-process drill-downs**.
- Working **time/value toggle** plus period, hourly-rate, recapture-rate, reset, and print controls.

Then perform a rendered browser check when browser/page tools are available:
1. Start `python scripts/serve_dashboard.py --dir output/team-dashboard` in a managed background
   terminal, then verify `/health` responds and open `http://127.0.0.1:7333/`. Use `--no-open` for
   headless verification. Do not open the HTML with `file://`: JSON fetches require the local server.
   If the host cannot run a persistent server, disclose it and provide the folder and launch command;
   never silently substitute the old single-file dashboard.
2. Visit all four tabs and confirm each required chart is visible.
3. Expand at least one business-process row.
4. Exercise the period/rate/recapture controls, the time/value toggle, Reset, and tab navigation.
5. Use screenshot verification when available.

If browser or screenshot tooling is unavailable, **say so clearly** and report that only the bundled
structural verifier ran. Never imply that rendered screenshots were checked when they were not.

**Block delivery if any required visual or control is missing, empty because aggregate inputs were
incorrectly removed, or broken.** Fix the data/rendering issue, rebuild with the bundled renderer,
and repeat verification. Do not email the dashboard or call the run complete until this gate passes.

### 6. Share a reviewed export — only on explicit request after verification
Building is not permission to send. Read `output/team-dashboard/team-summary.md` with the manager,
or use **Save / Print PDF** for the current dashboard view and inspect that PDF first.
Never attach the HTML alone (it requires sibling assets), the private working JSON, or the local URL.
Never send automatically, including when an older config has `email_on_run:true`. That legacy flag
may prompt an offer to share; it is not consent. Existing scheduled prompts must be updated to
build only rather than sending automatically.
- **Recipients = the channel members.** `ListChannelMembers(team_id, channel_id)` → resolve each to an
  email/UPN; de-duplicate; include the runner. (A standard channel returns the team members — that's
  the intended audience.) Never add anyone outside the channel.
- **Body = a high-level HTML summary** (aggregate only, same privacy rules as the dashboard). Use
  only the reviewed export's totals; never derive or disclose per-contributor figures or name a process that failed
  the cohort threshold. Do **not** attach or quote `working/team_data.json`.
- Show the exact recipients, subject, body and export attachment, then ask **Send / Edit / Cancel**.
  Only on Send, use the host's email tool with the reviewed export:
  ```
  SendEmailWithAttachments(
    to=<resolved channel-member emails>,
    subject="Team Cowork Team Report — latest rollup (<period>)",
    content_type="HTML", body=<summary html>,
    direct_attachment_file_paths=["output/team-dashboard/team-summary.md"])
  ```
  A Markdown export uses the build's default pricing; a printed PDF reflects the current controls.
  The "Powered by Copilot Cowork" footer is appended by the host — don't add your own.

### 7. Report delivery
After verification, report the local URL, folder, reviewed export and how to stop the server
(Ctrl+C in its terminal). Report email delivery only if an explicitly approved send succeeds.
Optionally show a **3-line** highlight (time saved, value, top process) — aggregate only.

**Keep the delivery message short. Do NOT prepend, attach, or post a separate "Coverage and
interpretation", "Source and coverage", caveats, limitations, assumptions, or methodology
banner/preamble** — not above the dashboard, not in the chat, and not in the email. All of that already
lives *inside* the dashboard: the header disclaimer, the "Generated … · latest channel rollup …"
context line, and the **How to read** tab. The `[parse_posts]` console lines (messages read, posts
kept, contributor counts) are **diagnostics for you only** — never surface them or expand them into a
coverage write-up.

### 8. (Optional) automate — run 1–2 days after the member fortnight
If the user asks, `SetupScheduledPrompt` with a self-contained description: *"Read the last 15 days of
Cowork Team Report posts in the team channel, aggregate them into the anonymized team dashboard (the how-to-read
guide is built into it), save the local site and Markdown summary to my files. Do not send or publish
anything; exports require a separate interactive review and approval."*

**Timing:** the Member skill prompts members to review and email reports on a **biweekly Monday**
cycle, so schedule the manager rollup to run **1–2 days later — on Wednesday** — which gives
teammates Monday and Tuesday to send before the
rollup reads the channel. Use frequency **Week**, `interval = cadence_days / 7` (= **2** → every other
Wednesday), `weekDays=["Wednesday"]`, `hours=["9"]`, name "Cowork Team Report team dashboard". Scheduled runs
must use the bundled renderer and pass `verify_dashboard.py`. Scheduled builds do not send exports
or add start-at-login integration. A verification failure blocks completion.

## Privacy (hard rules)
- **Never publish contributor-level records or links between contributors and metrics.** The parser's
  working JSON contains these only as a private intermediate; the local public JSON contains a separate aggregate
  contract with no member records or role assignments.
- **Cohort threshold:** every category, process, role, skill, deliverable format, fit grade, and
  secondary detail is included only when **≥ `privacy_k_threshold`** (default **3**) distinct
  contributors support it. Suppress small residual pools unless their combined contributor count
  also meets the threshold.
- **Never publish** names, country, raw filenames, prompts, JTBD prose, deliverable names, individual
  task rows, or per-item dates. Process detail is restricted to threshold-qualified format and skill
  totals.
- **The email body is aggregate-only too** — same rules; no member is ever named or singled out.
- The dashboard is designed for team-level sharing. It exposes team totals and cohort-qualified
  breakdowns, not who did what. Keep `working/team_data.json` private and never send it as an
  attachment.

## Cross-skill contract (keep in sync)
This skill can only aggregate what **`cowork-dashboard-member`** emails into the channel. These must match its copies or
aggregation breaks — **change them in both bundles together**:

| Item | This skill | Must match |
|---|---|---|
| Business-process **grouping** | `scripts/process_groups.json` | `cowork-dashboard-member/scripts/process_groups.json` (and `cowork-roi-report`'s copy) — **byte-for-byte** |
| **Skills** vocabulary | `scripts/skills_vocabulary.json` | `cowork-dashboard-member/scripts/skills_vocabulary.json` (and `cowork-roi-report`'s) — **byte-for-byte** |
| **Roles** taxonomy | `scripts/roles_taxonomy.json` | `cowork-dashboard-member/scripts/roles_taxonomy.json` — **byte-for-byte** |
| **Value pillars** | `references/value-pillars.md` | `cowork-dashboard-member/references/value-pillars.md` — **byte-for-byte** |
| **Role** attribute + no country/names | reads the report header `Role:` line | `cowork-dashboard-member/scripts/format_member_message.py` (emits `Role:`; excludes country/names) |
| Deliverable → process link + **by-type** rollup | parser reads the "By type" deliverables table | `format_member_message.py` (that rollup "is also what the aggregated Dashboard reads") |
| The **shared channel** | `channel_id` resolved from the link the user pastes | the channel whose email address is stored in `cowork-dashboard-member/config/team_channel.json` — must be the same channel |

- `scripts/skill_aliases.json` is a **reader-only** compatibility shim (maps older non-canonical skill
  labels → the vocabulary). It is **not** part of the shared contract and lives only here.
- **Deliverable NAMES:** the Member skill **strips file names by design** (emits
  Type/Date/Process/Skills/Hours/Value — no names). To show doc names, the Member skill must first add
  an opt-in name manifest; only then can this reader surface a manager-only named list. That is a
  **Member-skill change** — flag it before promising named deliverables.

## Guardrails
- **Bundled renderer is mandatory.** Always build with `scripts/build_outputs.py`; never substitute a
  simplified layout or hand-authored summary.
- **The public-data boundary is mandatory.** Never embed `team_data.json` directly. The renderer
  builds a separate aggregate-only payload and suppresses any breakdown below the configured cohort
  threshold while preserving the dashboard controls and aggregate visual surfaces.
- **Required visuals are a delivery contract.** Waterfall, category bars, stacked mix,
  process drill-downs, and the time/value toggle must all pass verification before email.
- **No verification, no delivery.** Missing or broken required visuals block email and completion;
  fix, rebuild, and re-test instead.
- **No fabricated data.** Every number traces to a post via the pipeline. Empty sections are omitted;
  an empty 15-day window yields no dashboard, not a made-up one.
- **No hand math.** `parse_posts.py` totals; `build_dashboard.py` prices at the live rate; the email
  figures are read from `team_data.json`.
- **Local-site output.** Keep HTML, CSS, JavaScript and public JSON separate, without CDN dependencies.
  The server binds only to loopback and serves an explicit public-file allow-list. It is read-only:
  no refresh/job/command routes, so no command token is needed. If acting routes are ever added,
  require POST, a per-process token, exact Origin/Host checks and fixed argv-only job definitions.
- **Latest report wins, within the window.** The reader keeps only the last 15 days, then the most
  recent report per sender; re-running a member report replaces the earlier contribution.
- **Channel is user-owned.** Read the channel resolved from the user's link; re-ask only if they name
  a different one. Never guess or construct a `channel_id`.
- **Email stays inside the channel.** Recipients are the channel members only; the body is
  aggregate-only. Interactive sends go through the approval dialog; honor "don't email" / `email_on_run:false`.

## Bundled files
- `SKILL.md`, `README.md`, `CHANGELOG.md`
- `config/team_config.json` — rate + k-threshold + cadence + 15-day lookback + email toggle; the
  channel IDs are filled in on first run (not shipped hard-coded).
- `scripts/resolve_channel.py` — parse a pasted Teams channel/message link → `team_id` + `channel_id`; persist to config (stdlib only).
- `scripts/make_invite.py` — render the inviting member "get started" message (channel post + email + plaintext + a personalized 1:1 DM via `--recipient-name`) with the download link baked in, so members are onboarded in-channel or direct-messaged 1:1 instead of hand-delivered a bare zip (stdlib only).
- `scripts/parse_posts.py` — channel posts → private `working/team_data.json` intermediate (stdlib only; 15-day window, latest-per-sender, groups processes, canonicalizes skills).
- `scripts/build_dashboard.py` + `assets/dashboard.html.template`, `assets/dashboard.css`,
  `assets/dashboard.js.template` — private intermediate → cohort-filtered aggregate-only local site.
  The build emits `index.html` and `assets/dashboard.js`. The `.template` suffix distinguishes
  bundled source from generated site files; it does not change the JavaScript or guarantee
  Microsoft Defender clearance.
- `scripts/serve_dashboard.py` — confined, read-only loopback server; opens the default browser
  unless `--no-open` is supplied. Ctrl+C stops it; no desktop icon or login integration is installed.
- `scripts/verify_dashboard.py` — mandatory structural/privacy gate for the four tabs, required
  aggregate visuals, controls, unresolved placeholders, local assets and public data.
- `scripts/build_guide_pdf.py` — **legacy** one-page landscape interpretation PDF (uses `reportlab`). Retained but off by default; the guide now lives inside the dashboard.
- `scripts/build_outputs.py` — the build step; renders the dashboard (guide built in). Pass `--with-pdf` to also regenerate the legacy PDF.
- `scripts/process_groups.json`, `scripts/skills_vocabulary.json`, `scripts/roles_taxonomy.json` — **mirrors** of the Member bundle (shared contract).
- `scripts/skill_aliases.json` — reader-only skill-label compatibility shim.
- `references/value-pillars.md` — **mirror** of the four-pillar crosswalk.
- `examples/sample_raw_messages.json` — two real, de-identified posts for an offline end-to-end test.

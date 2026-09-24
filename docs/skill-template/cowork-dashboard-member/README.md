# Cowork Team Report — Member skill (self-contained)

Emails a **de-identified, table-formatted** Cowork Team Report summary to your team's Teams channel
email address, with a **privacy opt-out** so you can remove any chat/task from the pending report
before it sends. Removing a
session from the report also removes its work artifacts; it does not delete the original Cowork session.
It harvests your own Copilot
Cowork sessions from OneDrive, computes research-anchored time-saved / value / speed metrics, and
renders them as HTML tables (headline KPIs, time-by-category, value pillars, jobs-to-be-done,
work-by-business-process, roles, skills, analyzed→produced, deliverables, activity-by-day). The email
header shows your **directory Role** (job title — no country, no name); the **business processes are
grouped** into a short canonical set; each **deliverable is shown and labelled with the business
process it supported** using a de-identified descriptive name rather than its raw filename; and
metric/section titles match the **Copilot ROI Report** skill.

> **Setting this up for a team?** This skill is one half of a two-part solution. See the
> [repository guide](../../README.md) for the full picture and the easiest way to roll it out — a page
> that bakes your team's channel email address into ready-to-install downloads.

## Download

Grab the whole skill as one file: [`cowork-dashboard-member.zip`](../cowork-dashboard-member.zip) —
the generic, un-customized copy for a manual install. (For a copy with your team's channel email
address already built in, use the Installer Studio page linked in the
[repository guide](../../README.md).)

## Install — one folder, no dependencies
This skill is **self-contained**: it bundles its own analysis pipeline (`classify.py`, `compute.py`,
taxonomy data, harvest references). You do **not** need `cowork-roi-report` or any other skill.

1. Copy the whole **`cowork-dashboard-member/`** folder into your Cowork skills directory:
   `Documentos/Cowork/skills/cowork-dashboard-member/`
2. Changes appear after OneDrive sync (~35 seconds).

That's it — nothing else to install, and no nested folders to flatten.

## First-time setup — for the admin / manager / lead (one time)

Before anyone runs the skill, your team needs **one** dedicated Teams channel for these reports,
created by the manager / admin / lead and enabled to receive channel email. This is a one-time setup.

1. **Create a Teams channel** named `Cowork Report - {your team}` (for example, `Cowork Report - ROI Advisors`).
2. **Invite everyone who will be measured** and add them as **owners** of the channel.
3. **Keep the channel data-only** — nobody should hold manual conversations in it, since stray messages can
   break the downstream rollup.
4. **Copy the channel email address** — open the channel's **⋯ More options** menu, choose
   **Get email address**, and configure the channel's email security settings to allow messages from
   your team members.
5. **Build the team-specific bundle** — put that address in `config/team_channel.json` as
   `channel_email`, or use the Installer Studio page from the
   [repository guide](../../README.md) to bake it into the download.

## Use it
Ask Cowork: **"email my Cowork Team Report stats to the team channel."** The skill will:
1. Ask whether to run **once** or **automate biweekly (every other Monday)** — this prompt appears on your **first run**, not at install.
2. Read the Teams channel email address already configured in the team-specific bundle.
3. Harvest your last-15-days Cowork sessions.
4. Show the **privacy opt-out** picker — every session is individually selectable; pick any to exclude.
5. Compute + render the table email and send it to the configured channel address (with the
   platform's approval dialog as the final gate).

On a **scheduled** run there's no one to answer the picker, so it **emails you** that the report is
ready and asks you to open the task chat to exclude sessions and send — it never auto-sends the
report to the channel.

## Before you share / first run
- **Team channel email (configured in the bundle):** the installer generator fills
  `config/team_channel.json` `channel_email` for each team. The member is never asked to choose a
  recipient. If it is missing or invalid, the skill stops instead of guessing or falling back to a
  Teams API post. Your team's admin/manager/lead must create the channel, enable its email address,
  and configure allowed senders first — see *First-time setup* above.
- **Per-user memory.** The taxonomy registry is scoped to whoever runs the skill:
  `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json`, owner-stamped, on that user's own
  mount. A **first run has no memory** and builds the user's processes from their own sessions;
  `reconcile_taxonomy.py` ignores any registry that isn't the invoking user's. **No seed ships.**
- **`scripts/process_overrides.json` ships empty (`{}`) and is vestigial** — the real per-run overrides
  are written to `working/process_overrides.json` at runtime, never into the bundle.
  `scripts/process_overrides.example.json` shows the format.
- The skill contains **no personal data** — no session names, prompts, harvested history, seed, or
  populated overrides. **Never** add any of those before sharing/zipping.

## Privacy
Before sending, you can remove any session you do not want included. That session and all of its work
artifacts are removed from the pending report before metrics are computed or anything is sent. This does
not delete the original session from Cowork.

Your individual identity, person name, prompts, and **country** never leave the machine, and raw file
names are replaced with de-identified descriptive labels.
The email carries aggregates — totals, categories, value pillars, roles, skills, deliverable/IO counts, and
the process / jobs-to-be-done tables (which may carry customer/account names) — plus your directory **Role**
(job title, a de-identified attribute) and only the sessions you kept. Retained work artifacts can appear
under de-identified descriptive names rather than raw filenames. When listing sessions to remove, the tool
reminds you to leave out anything personal or non-work, including artifact descriptions, that you
are not comfortable emailing to the channel.

## Optional hooks — capture chat-only sessions automatically

The Stop hook runs `/mnt/user-config/skills/cowork-dashboard-member/scripts/mine_session.py`
(or the identical `/mnt/user-config/skills/cowork-roi-report/scripts/mine_session.py` when that
sibling is installed). Use **one** capture hook, not two; keep the durable log at
`/mnt/user-config/.claude/cowork-session-telemetry.json`.

**First-run telemetry hook check:** if `/mnt/user-config/settings.json` is missing or lacks a Stop
hook pointing to an existing `mine_session.py`, the skill tells you **the forward-capture hook is
not active**. Merely installing the script does not enable the hook.

Capture reads the current Copilot `events.jsonl` (legacy Claude transcripts still work) and is
**forward-only**. OneDrive holds only file artifacts: past chat-only sessions require a separate,
optional backfill from the Cowork app's left-nav list. The skill asks once, reads **titles and dates
only — never chat contents or prompts** — and sends the added sessions through the normal privacy
picker before computing anything. Without browser access or consent, the report preview states the
coverage gap rather than guessing. Hook execution itself depends on runtime support/activation.

## Version history

Each release ships a `CHANGELOG-v<N>.md` document with the full notes. Newest first — the detailed
notes for the current release are below under **Updates in v27**.

| Version | Highlights | Details |
|---|---|---|
| **v27** _(current)_ | Email delivery to the configured Teams channel email address · no Teams API posting or first-run link prompt | [CHANGELOG-v27.md](CHANGELOG-v27.md) |
| **v26** | Restored current-runtime chat-only capture · legacy parser retained · consent-based historical title/date backfill before the privacy picker · first-run hook check | [CHANGELOG-v26.md](CHANGELOG-v26.md) |
| **v25** | Grouped business processes into a short canonical set · curated ~30-skill vocabulary · runner's **Role** shown in the header (no country/name) · every deliverable made visible and labelled by business process · verified that excluding a session removes its deliverables · privacy nudge at the exclude step · metric/section titles aligned to the **Copilot ROI Report** skill | [CHANGELOG-v25.md](CHANGELOG-v25.md) |
| **v24** | Per-user, owner-scoped taxonomy memory — fixes cross-user leakage; no seed ships; per-run overrides moved out of the bundle (`process_overrides.json` ships empty `{}`) | [CHANGELOG-v24.md](CHANGELOG-v24.md) |
| v1–v23 | Shared lineage with the sibling **`cowork-roi-report`** skill (harvest, classifier, research-anchored two-clock methodology, value pillars). See that skill's `CHANGELOG-v5…v22` documents. | — |

> **Downstream consumers.** The de-identified report this skill emails into Teams is read by two sibling skills:
> the **`cowork-roi-report-aggregated`** table report and the manager-side **`cowork-dashboard-team-dashboard`**
> rollup (which breaks out a Role only when ≥3 contributors share it). The **Role** attribute, the
> grouped **business-process** labels, the curated **skills** list, and the **deliverable → process**
> link are a shared contract — keep them in step with `cowork-roi-report`'s copies when you change them.

## What's inside
```
cowork-dashboard-member/
├── SKILL.md
├── README.md
├── scripts/
│   ├── prune_sessions.py          # privacy opt-out (list + drop sessions)
│   ├── mine_session.py            # live-session telemetry hook (exec_min, tool intensity, per-category runs)
│   ├── format_member_message.py   # renders the HTML table email
│   ├── classify.py                # ext→category classifier + process overrides + grouping
│   ├── compute.py                 # research-anchored two-clock model (+ pct_time, role, deliverable→process)
│   ├── apqc_taxonomy.json         # fallback business-process taxonomy
│   ├── process_groups.json        # canonical business-process grouping (shared w/ cowork-roi-report)
│   ├── roles_taxonomy.json        # professional-roles keyword fallback
│   ├── skills_vocabulary.json     # curated ~30-skill controlled vocabulary
│   ├── process_overrides.json     # ships empty {} (vestigial; real overrides go to working/)
│   └── process_overrides.example.json
└── references/
    ├── map-my-work-playbook.md    # derive process / pillar / JTBD per session
    └── value-pillars.md
```

## Updates in v27

_Full notes: [CHANGELOG-v27.md](CHANGELOG-v27.md)._

- Send the rendered HTML report through email to the Teams channel's configured email address.
- Read `channel_email` from `config/team_channel.json`; team-specific installers populate it.
- Remove the first-run channel-link prompt, Teams ID parsing, channel memory, and Teams API posting.
- Keep the mandatory interactive privacy review and platform approval before delivery.
- Keep scheduled runs review-only: they notify the member but do not send the report to the channel.

## Updates in v26

_Full notes: [CHANGELOG-v26.md](CHANGELOG-v26.md). Shared capture fix: `cowork-roi-report` v42._

- Discover the current `.copilot-state/*/session-state/*/events.jsonl` and parse its session id,
  first-user-message title, wall-clock duration, turns, tool starts, and output artifact evidence.
- Normalize current `server-Tool` names before applying the existing app/category rules.
- Add the optional, title/date-only historical backfill (§3b), with no fabricated transcript evidence
  and the same mandatory privacy picker. This release does **not** backfill history by itself.
- Document current installed script paths and check that the forward-capture hook exists.

## Updates in v25

_Full notes: [CHANGELOG-v25.md](CHANGELOG-v25.md). Aligned with `cowork-roi-report` v25._

This release acts on team-lead review feedback. Nothing about the harvest, the mandatory privacy
opt-out, the fixed team channel, the per-user taxonomy memory, or the research-anchored
methodology changed — only the post's content and de-identification.

**Added**
- **Privacy nudge at the exclude step.** When sessions are listed for exclusion, the skill reminds you
  to leave out anything personal or non-work you're not comfortable sharing — each session's
  deliverables go out with it.
- **Deliverables made visible & labelled by process.** The post now shows every deliverable
  (**Type · Date · Business process · Skills · Hours · Value**, no file names), followed by the
  by-type rollup.
- **Your Role in the header.** The runner's directory job title (e.g. "Business Value Advisor –
  Analytics") is shown. **No country, no name, no prompts; deliverables appear as de-identified
  descriptions, not raw file names.**

**Fixed / verified**
- **Excluding a session removes its deliverables.** The exclude step now proves it — it reports the
  deliverable count removed and verifies no remaining deliverable references an excluded session.

**Changed**
- **Grouped business processes** into one short canonical set (e.g. all skill/automation variants →
  *Skill Development*; finance + analytics/reporting → *Business Value & ROI Analytics*). Your per-user
  memory and Jobs-to-be-done stay granular — only the process label is grouped.
- **Curated skills** to a canonical, industry-relevant ~30 (18 domain + 12 tech).
- **Titles aligned to the Copilot ROI Report skill** — "Roles Cowork assembled for me",
  "Deliverables & the skills behind them", and headline metrics *Expert-equivalent hours /
  Professional-services value / Speed multiplier / Active days*.

**Keep in sync when you change these:** the **Role** attribute, the grouped **business-process**
labels, the curated **skills** list, and the **deliverable → process** link are shared with
`cowork-roi-report` (byte-identical taxonomy files) and read downstream by
`cowork-roi-report-aggregated` and the manager-side `cowork-dashboard-team-dashboard`.

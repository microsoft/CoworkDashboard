# Cowork ROI — Member skill (self-contained)

Posts a **de-identified, table-formatted** Cowork ROI summary to your team's Teams channel, with a
**privacy opt-out** so you can exclude any chat/task before it posts. It harvests your own Copilot
Cowork sessions from OneDrive, computes research-anchored time-saved / value / speed metrics, and
renders them as HTML tables (headline KPIs, time-by-category, value pillars, jobs-to-be-done,
work-by-business-process, roles, skills, analyzed→produced, deliverables, activity-by-day). The post
header shows your **directory Role** (job title — no country, no name); the **business processes are
grouped** into a short canonical set; each **deliverable is shown and labelled with the business
process it supported** (no file names); and metric/section titles match the **Copilot ROI Report** skill.

## Install — one folder, no dependencies
This skill is **self-contained**: it bundles its own analysis pipeline (`classify.py`, `compute.py`,
taxonomy data, harvest references). You do **not** need `cowork-roi-report` or any other skill.

1. Copy the whole **`cowork-roi-member/`** folder into your Cowork skills directory:
   `Documentos/Cowork/skills/cowork-roi-member/`
2. Changes appear after OneDrive sync (~35 seconds).

That's it — nothing else to install, and no nested folders to flatten.

## Use it
Ask Cowork: **"post my Cowork ROI stats to the team channel."** The skill will:
1. Ask whether to run **once** or **automate every 15 days**.
2. On your **first run**, ask you to paste the **Teams channel link** your admin/manager/lead shared
   (it parses the `team_id`/`channel_id` from the link and remembers them for next time).
3. Harvest your last-15-days Cowork sessions.
4. Show the **privacy opt-out** picker — every session is individually selectable; pick any to exclude.
5. Compute + render the table post and post it (with the platform's approval dialog as the final gate).

On a **scheduled** run there's no one to answer the picker, so it **emails you** that the post is
ready and asks you to open the task chat to exclude sessions and post — it never auto-posts.

## Before you share / first run
- **Team channel (asked on first run):** the skill is **not** tied to any one channel. On a member's
  first run it asks them to paste the **Teams channel link** their admin/manager/lead shared, parses
  the `team_id`/`channel_id` from it, and remembers them in a per-user memory file
  (`/mnt/user-config/.claude/cowork-roi-member-channel.<userkey>.json`) for later runs. Your team's
  admin/manager/lead must create that channel first — see the repo README's *First-time setup* section.
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
Person names, raw file names, prompts, and **country** never leave the machine. The post carries only
aggregates — totals, categories, value pillars, roles, skills, deliverable/IO counts, and the process /
jobs-to-be-done tables (which may carry customer/account names) — plus your directory **Role** (job
title, a de-identified attribute) — and only the sessions you kept. When listing sessions to exclude,
the tool reminds you to leave out anything personal or non-work you're not comfortable sharing.

## Version history

Each release ships a `CHANGELOG-v<N>.md` document with the full notes. Newest first — the detailed
notes for the current release are at the end of this README under **Updates in v25**.

| Version | Highlights | Details |
|---|---|---|
| **v25** _(current)_ | Grouped business processes into a short canonical set · curated ~30-skill vocabulary · runner's **Role** shown in the header (no country/name) · every deliverable made visible and labelled by business process · verified that excluding a session removes its deliverables · privacy nudge at the exclude step · metric/section titles aligned to the **Copilot ROI Report** skill | [CHANGELOG-v25.md](CHANGELOG-v25.md) |
| **v24** | Per-user, owner-scoped taxonomy memory — fixes cross-user leakage; no seed ships; per-run overrides moved out of the bundle (`process_overrides.json` ships empty `{}`) | [CHANGELOG-v24.md](CHANGELOG-v24.md) |
| v1–v23 | Shared lineage with the sibling **`cowork-roi-report`** skill (harvest, classifier, research-anchored two-clock methodology, value pillars). See that skill's `CHANGELOG-v5…v22` documents. | — |

> **Downstream consumers.** The de-identified post this skill publishes is read by two sibling skills:
> the **`cowork-roi-report-aggregated`** table post and the manager-side **`cowork-roi-team-dashboard`**
> rollup (which breaks out a Role only when ≥3 contributors share it). The **Role** attribute, the
> grouped **business-process** labels, the curated **skills** list, and the **deliverable → process**
> link are a shared contract — keep them in step with `cowork-roi-report`'s copies when you change them.

## What's inside
```
cowork-roi-member/
├── SKILL.md
├── README.md
├── scripts/
│   ├── prune_sessions.py          # privacy opt-out (list + drop sessions)
│   ├── format_member_message.py   # renders the HTML table post
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

## Updates in v25

_Full notes: [CHANGELOG-v25.md](CHANGELOG-v25.md). Aligned with `cowork-roi-report` v25._

This release acts on team-lead review feedback. Nothing about the harvest, the mandatory privacy
opt-out, the fixed ROI Advisors channel, the per-user taxonomy memory, or the research-anchored
methodology changed — only the post's content and de-identification.

**Added**
- **Privacy nudge at the exclude step.** When sessions are listed for exclusion, the skill reminds you
  to leave out anything personal or non-work you're not comfortable sharing — each session's
  deliverables go out with it.
- **Deliverables made visible & labelled by process.** The post now shows every deliverable
  (**Type · Date · Business process · Skills · Hours · Value**, no file names), followed by the
  by-type rollup.
- **Your Role in the header.** The runner's directory job title (e.g. "Business Value Advisor –
  Analytics") is shown. **No country, no names, no file names, no prompts.**

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
`cowork-roi-report-aggregated` and the manager-side `cowork-roi-team-dashboard`.


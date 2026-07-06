# CHANGELOG — v25 (aligned with cowork-roi-report v25)

Manager-feedback pass on the de-identified team-channel post. The shared data contract
(business-process labels, skills vocabulary, the new Role attribute, and the deliverable→process link)
is mirrored in `cowork-roi-report`; the aggregated **"Cowork report – ROI Advisors"** reader reuses
the report copies, so it stays in sync automatically.

## Added
- **Privacy nudge at the exclude step.** `prune_sessions.py --list` now prints a reminder to exclude
  anything personal or non-work you're not comfortable sharing before it posts (each session's
  deliverables go out with it). `SKILL.md` step 4 tells the agent to surface the same reminder on the
  opt-out picker.
- **Deliverables made visible + labelled by business process.** `compute.py` stamps each deliverable
  with its owning session's `process` (and `value_pillar`). `format_member_message.py` now renders a
  per-deliverable table — **Type · Date · Business process · Skills · Hours · Value** — followed by the
  existing **By type** rollup. De-identified: no file names.
- **Runner's directory Role.** `SKILL.md` step 2 selects `jobTitle`; the harvest writes `meta.role`;
  `compute.py` passes it through to the payload; `format_member_message.py` shows **Role: <title>** in
  the header. **No country, no names, no file names, no prompts.**
- **`scripts/process_groups.json`** — canonical business-process grouping map.

## Fixed / verified
- **Excluding a session removes its deliverables.** Deliverables ride inside each session's `outputs`,
  so dropping a session already dropped them; `do_drop` now proves it — it reports the deliverable
  count removed, defensively strips any parallel top-level deliverable/artifact entries keyed to the
  excluded sessions, and asserts no surviving deliverable references an excluded session.

## Changed
- **Grouped business processes.** `classify.py` normalises every process label (APQC fallback,
  registry-minted, or override) into one short canonical set via `process_groups.json`
  (`group_process`). e.g. all capability/skill-development variants → **Skill Development**; finance +
  analytics/reporting → **Business Value & ROI Analytics**. The per-user registry and Jobs-to-be-done
  stay granular — only the process *label* is grouped.
- **Curated skills vocabulary.** `skills_vocabulary.json` trimmed to a canonical, industry-relevant
  ~30 (18 domain + 12 tech); internal provenance/verbatim bookkeeping removed.
- **Titles aligned to the Copilot ROI Report skill.** "Roles Cowork stood in for" → **"Roles Cowork
  assembled for me"**; "Deliverables & the skills behind them — by type" → **"Deliverables & the
  skills behind them"**; headline metric names → **Expert-equivalent hours**, **Professional-services
  value**, **Speed multiplier**, **Active days**.

## Cross-skill (must stay in sync)
- **`cowork-roi-report`**: identical `skills_vocabulary.json`, `compute.py`, `process_groups.json`, and
  the same `group_process()` in `classify.py`; `build_report.py` shows the Role line. See its
  `CHANGELOG-v25.md`.
- **`cowork-roi-report-aggregated`** (the "Dashboard"): `format_aggregated_report.py` renders
  `meta.role` and a Deliverables-by-business-process table. It reuses the report pipeline, so grouped
  processes + curated skills flow automatically.

## Unchanged
The harvest, the mandatory privacy opt-out, the fixed ROI Advisors channel, the per-user owner-scoped
taxonomy memory, and the research-anchored two-clock methodology — all as in v24.

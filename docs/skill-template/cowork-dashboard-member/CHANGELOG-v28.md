# Cowork Team Report member v28

## Changed — task-category classifier aligned with `cowork-roi-report` v48

- `scripts/classify.py` ports the v44–v48 category rules from `cowork-roi-report`:
  - **One category per session** (was up to two).
  - **Final-output rule:** work that ends in an email (send / draft / reply / forward) or is inbox
    triage → **Email workflows**; otherwise posting to Teams or predominantly Teams-channel synthesis
    → **Communication workflows**.
  - **Skill work** (create / attach / install / package / quality-review a skill or plugin, or a
    `.zip`/`.skill` input or output) → **Write or debug code**; `.zip`/`.skill` now map to code.
  - **Research vs content:** research intent in the goal plus ≥3 gathered sources (when an action
    history exists) → **Analysis & Research**, even when the findings land in a deck or doc.
  - **Outside-M365 systems** (connectors or third-party MCP servers, e.g. Salesforce, ServiceNow,
    Jira, SAP) add **Specialized workflows** as a candidate.
  - **Ties** are broken by the format of the session's final deliverable (latest-created primary
    output), then by PRIORITY.
  - Each output's `created` timestamp is carried through to identify the final deliverable.
- `scripts/compute.py`: time saved is attributed to the session's single category; telemetry runs
  logged under other categories are dropped (not reassigned), so no session is double-counted.
- `SKILL.md` §3 harvest records each output's `createdDateTime` as `created`; §6 summarizes the
  ordered rules.
- New `references/classification-methodology.md` documents the full rule set and worked examples.

## Unchanged

- Business-process grouping (`process_groups.json`), the Cowork-fit grade, the email table layout,
  and the shared contract read by the manager dashboard.

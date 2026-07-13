# Changelog — Cowork Team Report Team Dashboard

All notable changes to this skill are documented here. Versions follow the family's convention
(the ROI skills version independently). Dates are ISO-8601.

## [1.4.0] — 2026-07-13

Second manager-review pass on the team dashboard. The interpretation guide moves *inside* the
dashboard, bar tracks align, type-only deliverables collapse, task-category derivation is explained,
and each task category now shows how many contributors used it.

### Added
- **In-dashboard "How to read" guide.** The former *Glossary & method* tab is renamed **How to read**
  and expanded into the full guide the standalone PDF used to carry — the five tabs, the KPI band, the
  two controls, the privacy model, the value model, the research bands, **how task categories are
  derived**, and **why some deliverables show only a file format**. Reviewers were missing the separate
  PDF attachment and toggling between two files; the guide now travels in the one file.
- **Per-section "?" helpers.** Every section title carries a clickable **"?"** that pops a one- or
  two-line plain-language explanation in place (click-to-toggle; closes on outside click).
- **Contributor reach per task category.** Each category row now shows how many contributors used it
  (e.g. "used by 4 of 5 contributors") so managers can see where usage is concentrated vs. spread —
  not just hours. **Privacy floor:** below `privacy_k_threshold` (default 3) the exact count is
  withheld and shown as "used by &lt;3 contributors". Aggregate counts only — never identities.

### Changed
- **Bar tracks are now uniform.** The value column in every bar row (`.row`) is a fixed width, so the
  gray track starts and ends at the same place on every row. Previously the `auto` value column sized
  to its own text, squeezing the `1fr` track by different amounts per row. Count-style rows
  (inputs/outputs) use a narrow `.rc` value column.
- **Type-only deliverables collapse per format.** In *Work by business process*, deliverables a post
  carried without a de-identified name now collapse into one row per format (e.g. "HTML · 5
  deliverables", hours/value summed) instead of repeating "HTML" many times. Named deliverables still
  list individually. Clarified that a format-only row means the name wasn't posted — not a
  recognition failure.
- **PDF guide retired from the default flow.** `build_outputs.py` now builds the dashboard only (the
  guide is inside it) and prints one line. The legacy `build_guide_pdf.py` is retained but **off by
  default**; pass `--with-pdf` to regenerate a printable copy. The email attaches only the HTML
  dashboard.
- **SKILL.md** updated throughout: intro, build step 4 (dashboard-only, guide built in), email step 5
  (single attachment), verify step 6, the scheduled-run description, and the bundled-files list.

### Verified
- Rebuilt dashboard: embedded data parses, the app JavaScript runs with no runtime errors under a DOM
  shim, 4 categories show exact reach and 2 fall under the `<3` floor, and type-only deliverables
  collapse to per-format rows. No taxonomy/parser change — the `cowork-dashboard-member` contract is intact.

## [1.3.0] — 2026-07-10

Manager-review follow-ups: robust ingestion, named deliverables under each process, a single build
step, and schedule guidance aligned to the member fortnight.

### Added
- **Named deliverables under each business process.** `parse_posts.py` now reads the Member skill's
  current per-deliverable table (`Deliverable | Type | Date | Business process | Skills | Hours |
  Value`) — the earlier reader only matched a legacy `Type`-first table, so de-identified deliverable
  **names were silently dropped**. *Work by business process* now lists the **distinct deliverables**
  directly under each (collapsed) process row — one level indented, with the **file format inline** on
  each — replacing the old group-by-format sub-table. (No Member-skill change; names were already
  posted, de-identified — never raw file names.)
- **Version collapse.** Deliverables sharing the same de-identified name within a process collapse
  into ONE entry: the final (latest) one is kept and annotated `+N versions`
  (e.g. `Cowork Team Report +4 versions`).
- **`scripts/build_outputs.py`.** One step that builds BOTH the HTML dashboard and the one-page PDF
  guide in a single invocation, so the manager approves the **build once, not twice**. It drives the
  two existing builders (still runnable individually). The **email send stays a separate, expected
  approval**.

### Changed
- **Ingestion guard.** `parse_posts.py` only parses messages that actually carry the de-identified
  stats tables (`has_stats_tables`, ≥ 2 recognized tables), so an attachment/zip share posted to the
  channel (e.g. a member-skill `.zip`) is skipped instead of mis-parsed.
- **Display-only label remap.** `build_dashboard.py` renders the grouped process label
  `Skill Development` as **`Cowork Skill Development`** at render time only; `process_groups.json`
  stays **byte-for-byte identical** across the member, dashboard, and report bundles (verified md5).
- **SKILL.md / README.** Build steps 4 (dashboard) and 5 (PDF) merged into one `build_outputs.py`
  step; remaining steps renumbered (email → 5, verify → 6, automate → 7) with the email called out as
  a separate approval. Automate guidance now schedules the rollup **1–2 days after the member Monday
  fortnight — on Wednesday** (Week / interval 2 / Wednesday / 09:00), giving teammates Mon+Tue to post
  first.

### Verified (no change needed)
- Disclaimer sits in the top blue header; deliverable types render as real file formats
  (PPTX/Excel-CSV/Word/PDF/HTML/Image); skills remain nested under *Roles Cowork stood in for* with no
  duplicate standalone skills section. Deliverable **names in a collapsible element** — the item that
  had regressed — is restored by the parser + list changes above.

## [1.2.0] — 2026-07-08

Dashboard changes from manager review of the first team rollup.

### Changed
- **Disclaimer folded into the blue header (small print).** The "read as modeled tool-impact, not
  performance scores — read with team context (phase, seasonality); anonymized" framing now sits in
  the blue title header in small letters (not a separate yellow banner card), and was removed from the
  Overview insights grid where it had been buried.
- **Deliverables by FILE FORMAT, not overlapping type.** Types that overlapped (Text / File / Deck /
  Document) are relabeled to concrete formats — PPTX, Word, Excel/CSV, PDF, HTML, Image, etc. The
  repeated "skills behind them" pill column was dropped from this table.
- **Skills consolidated under Roles.** The standalone "Skills applied" section was removed from *How
  Cowork is used*; skills now appear once, as a collapsible "Skills behind these roles" detail under
  *Roles Cowork stood in for* — removing the skills/roles duplication the reviewer flagged.

### Added
- **Expandable business-process accordion.** `parse_posts.py` now also reads each post's per-deliverable
  table (Type · Date · Process · Skills · Hours). *Work by business process* is now an accordion: **each
  process row expands** to show the deliverable **formats** it produced (count · hours · value) and the
  **skills** behind them. When a process has many distinct skills, the skills **collapse into a nested
  sub-expand** to keep the row compact and navigable. File names remain excluded by design (Member
  skill); names will surface automatically if a future Member post opts in to sharing them.

## [1.1.0] — 2026-07-07

Channel is no longer hard-coded, the read window is fixed to the latest 15 days, and the dashboard is
now emailed to the channel members with a one-page interpretation guide.

### Added
- **First-run channel link.** The channel is no longer shipped in the config. On first run (any of
  `team_id`/`channel_id` blank) the skill **asks the user to paste the Teams channel link** and
  resolves the IDs from it via the new **`scripts/resolve_channel.py`** (extracts the `19:…@thread.…`
  channel id and the `groupId` team id, persists them + `channel_link` to the config). No Graph call
  needed; later runs reuse the saved IDs.
- **One-page interpretation guide.** New **`scripts/build_guide_pdf.py`** renders a single **landscape**
  PDF (`output/how-to-read-team-roi-dashboard.pdf`) explaining every KPI, the five tabs, the two
  controls, the privacy model, and the methodology (reportlab; team name + rate pulled from the data).
- **Email to channel members.** After building, the skill emails the **channel members**
  (`ListChannelMembers` → resolved emails) a high-level, aggregate-only HTML summary with the **HTML
  dashboard and the PDF guide attached** (`SendEmailWithAttachments`). Gated by the new
  `email_on_run` config flag (default true); recipients never extend beyond the channel.

### Changed
- **15-day window every run.** `parse_posts.py` gained `--window-days` (+ `--now` anchor); it drops
  posts older than the window **before** the latest-post-per-sender dedupe, so each run reflects only
  the latest cycle. `message_lookback_days` default lowered from 30 → **15**.
- **Config.** `team_id`/`channel_id`/`channel_name` ship **blank** (filled on first run); added
  `channel_link` and `email_on_run`. The old "skill creates the channel" setup flow was removed — the
  channel is expected to exist and is provided by link.
- **SKILL.md** rewritten: first-run link flow, 15-day + latest-per-sender read, PDF-guide step,
  email-to-members step, a new **"When NOT to Use"** section, and updated guardrails and bundled-files
  list. Header now tolerates a blank `team_name` (falls back to "Team").

## [1.0.0] — 2026-07-01

First release. Manager-side rollup that reads teammates' de-identified Cowork Team Report posts from a
shared Teams channel and renders one self-contained, anonymized HTML dashboard.

### Added
- **Setup flow (Teams channel).** `SKILL.md` documents the end-to-end channel setup: the Team must
  pre-exist; the skill **can create the channel** inside it (`CreateChannel`) if missing; it resolves
  IDs via `ListTeams`/`ListChannels` and persists them to `config/team_config.json`; permissions
  (`ChannelMessage.Read.All` to read, `ChannelMessage.Send` to post, `Channel.Create` to create) are
  spelled out; and the `channel_id` is called out as a **shared constant with `cowork-dashboard-member`**.
- **`config/team_config.json`** — single source of truth for channel identity, rate, cadence,
  `privacy_k_threshold`, lookback, and optional `team_size`.
- **`scripts/parse_posts.py`** — stdlib-only parser: reads channel posts (Graph or simplified shape),
  keeps the latest post per sender (id hashed away), matches tables by header signature (tolerant of
  metric wording drift), extracts the **Role** header line, **groups business processes**
  (`process_groups.json`) and **canonicalizes skills** (`skills_vocabulary.json` + `skill_aliases.json`),
  and emits an anonymized `team_data.json`.
- **`scripts/build_dashboard.py`** — renders `team_data.json` into a self-contained HTML dashboard with
  five small, single-purpose tabs (Overview · Impact & Value · How Cowork is used · Trends · Glossary),
  a live hourly-rate control, and a print/PDF button. Value = hours × rate throughout.
- **Privacy k-anonymity.** Nothing is shown at an individual level; a Role breaks out only when
  **≥ `privacy_k_threshold`** (default 3) contributors share it, else contributors collapse into one
  combined bar.
- **Mirrored shared taxonomies** (byte-for-byte from `cowork-dashboard-member`): `process_groups.json`,
  `skills_vocabulary.json`, `roles_taxonomy.json`, `references/value-pillars.md`. Verified via md5.
- **`scripts/skill_aliases.json`** — reader-only compatibility shim mapping older non-canonical skill
  labels onto the canonical vocabulary (not part of the shared contract).
- **`examples/sample_raw_messages.json`** — two real, de-identified posts for an offline end-to-end test.
- **README + CHANGELOG** for external publishing.

### Design decisions (from product feedback)
- **Removed** the Adoption tab, the Correlate (role↔skill/pillar) view, the **country** attribute, all
  per-member/org-attribute breakdowns on the value-contribution visual, and the daily heatmap.
- **Kept** Impact & Value and made **business process the spine** of "How Cowork is used".
- **Trends kept minimal** — one point per posting cycle (Cowork is used for specific tasks, not all day).
- **Removed cross-page repetition** — each metric now has exactly one home (KPI band, pillars donut,
  categories, and trend are no longer duplicated across tabs).

### Fixed
- Deliverable-type column rendered `undefined` (read the wrong field) — now shows Web page / Text / PDF /
  Deck / Image / Document correctly.
- Headline parsing: "Expert vs assisted hours" was swallowed by an over-greedy match (assisted → 0);
  "Hours / active day" overwrote "Active days" via a substring match; and the low/high range was
  double-counted in the browser aggregate. All three corrected and verified against the real posts
  (team: 54.2 h saved, 6.3× speed, range 26.0–83.2 h).

### Known limitations / future
- **Small homogeneous teams only** (v1). Org-wide / large-team / multi-channel aggregation is not solved.
- **Deliverable names** are not shown — `cowork-dashboard-member` strips file names by design. A named
  manager-only view requires a Member-skill change (opt-in name manifest) first.
- Role attribute is often absent in current posts, so most small teams render a single combined bar
  (correct, privacy-preserving) until Role is present for ≥ 3 sharers.

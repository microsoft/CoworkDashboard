# Changelog — Cowork Team Report Team Dashboard

All notable changes to this skill are documented here. Versions follow the family's convention
(the ROI skills version independently). Dates are ISO-8601.

## [1.10.0] — 2026-09-17

Adds a 1:1 onboarding path and tightens the invite's privacy wording. No dashboard-render or
parser-contract changes.

### Added
- **Send the member skill to teammates 1:1.** On first run (or on request), the skill now offers to
  deliver the member skill directly to specific people: collect emails (typed or picked from the
  channel), resolve names, render a personalized DM, **show recipients + a sample and require explicit
  confirmation**, then direct-message each person and report per-recipient results. See SKILL.md
  *First run — offer to send the member skill to teammates 1:1*.
- `scripts/make_invite.py --recipient-name` renders a personalized 1:1 DM variant between
  `<<<MEMBER-INVITE-DM>>>` / `<<<END-DM>>>`.
- **Install→setup bridge.** The Installer page and README now tell managers to say *"install … then
  walk me through setup — starting with sending the member skill to my team,"* and the skill's
  triggers + first-run ordering lead with the 1:1 share step. Installing alone runs nothing, so this
  makes onboarding (and member distribution) start immediately instead of the manager installing and
  walking away to an empty dashboard.

### Changed
- Invite copy no longer claims "no file names ever leave your machine." It now states the actual
  mechanism: personal names and prompts are excluded and **raw file names are replaced with
  de-identified descriptions**. Aligned across the member skill SKILL.md/README and the Installer page.

## [1.9.0] — 2026-09-11

Adds a **Cowork-fit** view and an **Overview measure toggle**, plus two impact-table display
refinements. All changes are dashboard render + de-identified member-post additions; the parser
contract keys off table-header cells and is unchanged for existing tables.

### Added
- **Cowork-fit composition waterfall** (How Cowork is used → *Cowork fit*). Every graded task is
  rated High / Medium / Low on how well it suited Cowork's agentic, cross-app strengths and shown as
  a stepped waterfall where the three bands add up to all graded hours (consistent with the value
  math — no separate "realizable" number). Click a band to expand its de-identified tasks (business
  process + method + hours only; never a person, file, or prompt).
- **"Assisted Time / Assisted Value" toggle** on the Overview tab. Switches the headline narrative
  and highlights the matching KPI between hours saved and dollar value; defaults to Assisted Time and
  is restored by Reset.

### Changed
- **Cowork fit** now renders **above Category mix** on the *How Cowork is used* tab.
- **"Roles Cowork stood in for"** lists the **top 10** roles with a "showing top 10 of N" note.
- **"Outputs produced — by format"** shows **counts only** (dollar/hours columns removed; per-item
  value still available under *Work by business process*).



Adds a **productivity recapture rate** — the share of modeled time savings a team can realistically
harvest into productive output — as a first-class, viewer-adjustable input alongside the hourly rate.
No parser/taxonomy or cross-skill contract changes (dashboard render + config layer only).

### Added
- **`recapture_rate` in `config/team_config.json`** (default `0.70`). Seeds the dashboard; every
  value / cost-reduction figure is now `time saved × recapture rate × hourly rate`.
- **Live "Recapture rate" control** in the dashboard control bar (0–100%), next to the hourly-rate
  box, with Reset support. Adjusting it re-prices every dollar figure instantly; time-saved hours and
  counts are unchanged.
- **"Effective time recaptured" KPI** = time saved × recapture rate — the productive hours the team
  actually reclaims, which is what the value figure prices.
- Glossary + value-model entries for **Recapture rate**, **Effective time recaptured**, and the
  updated **Value / cost reduction** formula.

### Changed
- The Overview headline, KPI value, category / role / skill / process / deliverable tables, and the
  fortnightly trend all price value at the recaptured rate.
- `parse_posts.py` passes `defaultRecapture` through to `team_data.json` meta (read from config).

## [1.7.0] — 2026-08-03

Fifth review pass — made the dashboard interactive and finished the guide-tab cleanup (no
parser/taxonomy or cross-skill contract changes; dashboard render layer only).

### Added
- **Glossary hover tooltips.** Every KPI label in *Team impact at a glance* shows its definition on
  hover/focus, generated from the Glossary at build time (single source of truth — edit the glossary
  and the tooltip updates).
- **Click-to-navigate deep links.** The labeled headers in the Overview "Where did we save the most
  time" card jump to the relevant tab and scroll to the section (Task Category → *Impact & Value*;
  Business Process → *How Cowork is used*).
- **Cross-reference links throughout.** Every place the body text names another tab or section is now a
  link that switches tabs, auto-expands the target guide section, and scrolls to it. Consistent
  formatting: referenced **tabs** are italic (no quotes), referenced **sections** are quoted (no
  italics); links use a muted gray dotted underline rather than bright blue.
- **Category total row.** *Where the time went — by task category* now ends with a Total row (hours ·
  value · run tasks) summed across categories.
- **Outputs-produced clarifier footer.** A note explaining that its hours/value cover only work tied to
  a produced output, so overall time saved may be higher (analysis/research/etc. that produced no
  distinct output).

### Removed
- **Guide-tab consolidation (continued).** Removed the *How to read this dashboard*, *The five tabs*,
  and *The KPI band* sections (content lives in the header and Glossary now). *Value model* converted to
  a bulleted list.

## [1.6.0] — 2026-07-31

Fourth review pass — removed the Business Value Pillar dimension entirely from the dashboard, and a
further copy/structure cleanup of the guide tab and header (no parser/taxonomy or cross-skill contract
changes).

### Removed
- **Business Value Pillar dimension.** Dropped the value-pillar donut section (Impact & Value), the
  Business Value Pillar column from the Overview "Where did we save the most time" card (now two
  columns), the pillar glossary entry and the "Value pillars" guide section, plus the supporting code
  (`renderDonut`, `PILL_COLOR`, the pillar color CSS vars, the pillar aggregation). The data pipeline
  still reads pillar data from posts (unused now) to keep the mirrored taxonomy/contract intact.
- **Guide-tab consolidation.** Removed four now-redundant "How to read" sections — *How to read this
  dashboard*, *The KPI band*, *Deliverables — and why some show only a file format*, and *The two
  controls* — folding their reader-useful content into the page header (orientation + controls notes)
  and the *Work by business process* subheader. The KPI definitions already live in the Glossary.

### Changed
- **Glossary edits.** Removed "Roles Cowork stood in for"; renamed "Run tasks" → "Tasks" then back to
  "Run tasks" for the metric label; added a real definition of a task; tightened Sessions, Team speed
  multiplier, Skills, Business process, Business value pillar (since removed), Deliverables, Time saved,
  and Task category. "Expert-equivalent" wording replaced with "manual" throughout the visible copy.
- **Header.** Retitled earlier to "Cowork Team Dashboard"; header now also carries the reader
  orientation and the Period/Hourly-rate controls guidance.
- **Copy cleanup.** "task-category" → "task category"; every "e.g." → "e.g.,"; the *How task categories
  are derived* signals converted to bulleted lists; assorted subheader rewrites (Where the time went
  reach note, Outputs-produced clarifier, Trends).

## [1.5.0] — 2026-07-30

Third review pass — a copy-and-visual polish of the dashboard (no parser/taxonomy or cross-skill
contract changes). Wording made plainer and more customer-facing, the value-pillar donut recolored,
category-mix and research-band data made more legible, the Overview auto-insights restructured into a
labeled summary, and a full alphabetized glossary added.

### Added
- **Glossary of terms** on the guide tab. A new alphabetized glossary (Active days … Value / cost
  reduction) defining every metric and label the dashboard uses, consistent with the reworded copy
  (e.g. Deliverables = distinct vs Outputs = every file/version). It leads the tab and opens expanded.
- The guide tab is renamed **"How to read + Glossary"** (label italicized so it stands out).

### Changed
- **Value-pillar donut recolored + hardened.** Pillars now use a sequential **slate-blue → periwinkle**
  ramp (`#3d4a68 · #6f7c9c · #a6afc7 · #dde2ee`) instead of four category-like hues, so the section
  reads as one coordinated family and no longer collides with any task-category color. Slices gained a
  theme-aware **hairline border** (`--donut-edge`, translucent in light/dark) and the legend swatches a
  matching outline, so the pale light end stays legible on the white card.
- **Analyzed → Produced recolored** off the task-category palette — inputs **amber-gold** (`#d99c1e`),
  outputs **magenta** (`#b4009e`); its under-chart note reworded to reference "outputs," not deliverables.
- **Research bands are now a table.** The guide's run-on band list became a visual table (one row per
  task category, color-swatched to match the charts, low / typical / high columns) with the citations
  moved into a footnote. Each category's per-bar band line now reads "Time range: low / **typical** / high".
- **Category mix** now shows each category's share as a **% label inside wide bar segments** and, in the
  legend, an adjacent **(% · hours)** per category; the privacy note was simplified.
- **Overview auto-insights restructured.** The headline (reworded to a plain "Cowork helped the team
  save … enabling tasks to be completed N× faster, with an estimated value of $X") stays its own
  full-width card; the top task category, business process, and value pillar are combined under a
  **"Where did we save the most time:"** card as three labeled columns (**Task Category / Business
  Process / Business Value Pillar**), each showing the area name and its time saved (hours · % of total).
- **Impact & Value** table relabeled **"Outputs produced — by format"** with a note that it counts each
  file and version, so it can exceed the Overview "Deliverables" KPI (distinct deliverables).
- **KPI band** reworded: "expert work-weeks" → "weeks"; the speed tile subtitle reads "hands-on compared
  to … without Cowork"; Sessions reads "N tasks were run across M sessions"; Hands-on time and Active
  days swapped, and "expert-equivalent" → "estimated without Cowork".
- **Title & header.** Report retitled **"Cowork Team Dashboard"** (browser tab too); subtitle now
  "Team Impact & how Cowork is used"; the header disclaimer rewritten to plainer, customer-facing copy.
- **Plainer section copy throughout** — new customer-facing subheaders on *What the data says*,
  *Business value pillars*, *Where the time went — by task category*, and *Time saved over time*; the
  *Work by business process* intro simplified and its redundant under-table note removed.

### Verified
- Offline sample pipeline (`parse_posts.py` → `build_outputs.py`) runs clean; the embedded dashboard
  JavaScript executes with no runtime errors under a DOM shim. No change to `parse_posts.py`, the
  taxonomy mirrors, or the `cowork-dashboard-member` contract.

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

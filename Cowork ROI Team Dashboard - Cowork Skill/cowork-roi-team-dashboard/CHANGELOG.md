# Changelog — Cowork ROI Team Dashboard

All notable changes to this skill are documented here. Versions follow the family's convention
(the ROI skills version independently). Dates are ISO-8601.

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

First release. Manager-side rollup that reads teammates' de-identified Cowork ROI posts from a
shared Teams channel and renders one self-contained, anonymized HTML dashboard.

### Added
- **Setup flow (Teams channel).** `SKILL.md` documents the end-to-end channel setup: the Team must
  pre-exist; the skill **can create the channel** inside it (`CreateChannel`) if missing; it resolves
  IDs via `ListTeams`/`ListChannels` and persists them to `config/team_config.json`; permissions
  (`ChannelMessage.Read.All` to read, `ChannelMessage.Send` to post, `Channel.Create` to create) are
  spelled out; and the `channel_id` is called out as a **shared constant with `cowork-roi-member`**.
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
- **Mirrored shared taxonomies** (byte-for-byte from `cowork-roi-member`): `process_groups.json`,
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
- **Deliverable names** are not shown — `cowork-roi-member` strips file names by design. A named
  manager-only view requires a Member-skill change (opt-in name manifest) first.
- Role attribute is often absent in current posts, so most small teams render a single combined bar
  (correct, privacy-preserving) until Role is present for ≥ 3 sharers.

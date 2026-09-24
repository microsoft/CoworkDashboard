# Cowork Team Report — Team Dashboard

A Microsoft Copilot **Cowork skill** that rolls up a small team's Copilot Cowork ROI. It reads the
de-identified stats each teammate emails to a shared Teams channel and renders **one self-contained,
anonymized HTML dashboard** the manager can open, re-price with a live hourly-rate control, and print.
It then **emails the channel members** a high-level summary with the dashboard attached. The guide for
reading it is **built into the dashboard** — a **How to read** tab plus a clickable **"?"** on every
section — so there's no separate file to open. The bundled renderer produces four tabs:
**Overview**, **Impact & Value**, **How Cowork is used**, and **How to read + Glossary**. On first run
it **asks for the Teams channel link** and
remembers it; every run reads the **latest 15 days** of messages, keeping the latest report per person.

> **Team-safe by design.** Individual identity, raw filenames, prompts, and country are not revealed.
> Retained work artifacts may appear under de-identified descriptive names. Before publishing, each
> teammate can remove any session from the pending report, which also removes that session's artifacts;
> a Role breaks out only when at least **3** contributors share it.

## The three-skill family

| Skill | Role | Output |
|---|---|---|
| `cowork-roi-report` | A person's **full** personal impact report | Rich HTML web app (their own view) |
| `cowork-dashboard-member` | A person emails their **de-identified** stats to the team channel | HTML tables in Teams |
| **`cowork-dashboard-team-dashboard`** (this) | The **manager** aggregates everyone's reports | Anonymized team HTML dashboard (how-to-read guide built in), emailed to the channel members |

This skill **only consumes** what `cowork-dashboard-member` emails into the channel. It does not harvest OneDrive and never
sees identities.

## Scope (v1)

Small, **homogeneous** teams (people doing similar work) at the **team level** — a handful of
contributors on one channel. Org-wide / large-team / multi-channel aggregation is intentionally out
of scope for now.

## Data flow

```
first run: user pastes channel link ──(scripts/resolve_channel.py)──▶  team_id + channel_id  ──▶ config

teammates ──(cowork-dashboard-member email)──▶  Teams channel  ──(ListChannelMessages)──▶  raw_messages.json
                                                                                     │
                                                              scripts/parse_posts.py │  (last 15 days,
                                                              + process_groups.json  │   latest per sender,
                                                              + skills_vocabulary    │   group processes,
                                                              + skill_aliases         ▼   anonymize → role only)
                                                                                team_data.json
                                                                                     │
                                     scripts/build_outputs.py ──▶ build_dashboard.py │  (k-anonymity, live rate,
                                     (guide built into the dashboard's               ▼   How-to-read tab + "?" helpers)
                                      "How to read" tab)              output/cowork-team-roi-dashboard.html
                                                                                     │
                                                          SendEmailWithAttachments ──▶ channel members
                                                          (high-level summary + the dashboard attached)
```

## Quick start

1. **Point it at the channel** (first run only). The skill asks for the **link of the Teams channel**
   where the team emails its Cowork Team Report stats (in Teams: channel ⋯ → *Get link to channel*), then
   resolves + saves the IDs:
   ```bash
   python scripts/resolve_channel.py --link "<pasted channel url>" --config config/team_config.json
   ```
   The Team must already exist and you must be a member. The channel **must match** the one
   whose email address is configured in `cowork-dashboard-member`. (See `SKILL.md → First run`.)
2. **Read + build (last 15 days) — dashboard + guide in one step:**
   ```bash
   # after saving the channel messages' `value` array to working/raw_messages.json
   python scripts/parse_posts.py --in working/raw_messages.json \
          --config config/team_config.json --out working/team_data.json --window-days 15
   python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
   ```
   This command uses the bundled renderer and runs `verify_dashboard.py`. It fails if any required
   aggregate visual, control, tab, or privacy check is missing.
3. **Verify before email.** When browser tools are available, open the generated HTML, visit all four
   tabs, exercise the controls, expand a process drill-down, and verify the waterfall, category bars,
   stacked mix, and time/value toggle. Use screenshot verification when available; disclose when it
   is unavailable. A failed check blocks delivery.
4. Open `output/cowork-team-roi-dashboard.html`; only after verification passes does the skill email
   it to the channel members. (The
   how-to-read guide is inside the dashboard — open the **How to read** tab or click any **"?"**.)

## Mandatory dashboard contract

- Build only with `scripts/build_outputs.py`; never substitute a simplified layout.
- Privacy cleanup removes identifying data, not aggregate chart inputs or visuals.
- Required visuals: Cowork-fit waterfall, category bars, stacked category mix, expandable
  business-process drill-downs, and the time/value toggle.
- `scripts/verify_dashboard.py` must pass before email delivery.
- If any required visual or control is missing or broken, fix and rebuild instead of sending an
  incomplete dashboard or calling the run complete.

### Try it offline (no Teams needed)

Two real, de-identified channel messages are bundled:

```bash
python scripts/parse_posts.py --in examples/sample_raw_messages.json \
       --config config/team_config.json --out working/team_data.json \
       --window-days 15 --now 2026-07-02 --generated 2026-07-01
python scripts/build_outputs.py --in working/team_data.json --config config/team_config.json
```

## Config (`config/team_config.json`)

| Key | Meaning |
|---|---|
| `team_id`, `channel_id` | Where to read (authoritative). **Blank until first run**, then filled by `resolve_channel.py` from the pasted link. |
| `channel_link` | The Teams channel URL the user pasted on first run (kept for reference). |
| `hourly_rate` | Default $/hr for the value model (adjust live in the UI). |
| `recapture_rate` | Productivity recapture rate `0–1` (default **0.70**): the share of time saved the team realistically harvests. Value = time saved × recapture rate × hourly rate. Adjustable live in the UI. |
| `cadence_days` | Report/refresh cadence (default 14). |
| `message_lookback_days` | Window each run reads — **default 15** (the latest cycle). Enforced by `--window-days`. |
| `privacy_k_threshold` | Minimum contributors sharing an attribute before it breaks out (default 3). |
| `email_on_run` | When true (default), email the channel members the dashboard (guide built in) after building. |
| `team_size` | Optional; v1 shows a contributor count, not adoption %. |

## Privacy model

- Members are **counts + a number**, never named.
- Before emailing the report to the channel, each member can remove any session they do not want included. Its
   artifacts are removed with it before metrics are computed; the original Cowork session is not deleted.
- The only personal attribute is the directory **Role** a post carries — never identity, country, raw
   filenames, or prompts.
- Retained work artifacts may be shown under de-identified descriptive names so the team can understand
   what was produced.
- **k-anonymity:** per-Role breakdowns require ≥ `privacy_k_threshold` contributors; otherwise they
  collapse into one combined bar. Small teams typically show a single combined bar.

## Shared taxonomy contract (keep in sync)

`process_groups.json`, `skills_vocabulary.json`, `roles_taxonomy.json`, and
`references/value-pillars.md` are **byte-for-byte mirrors** of the `cowork-dashboard-member` bundle (which
in turn mirrors `cowork-roi-report`). If those change, update this copy too or team aggregation
drifts. `skill_aliases.json` is reader-only and not part of the contract.

**Deliverable names:** the Member skill emits **de-identified descriptive names** (never raw file
names), but a post can also carry a compact **type-only** line with no name. Named deliverables list
individually under each business process — repeated versions of the same name collapse into one
`+N versions` entry — with the file format inline. **Type-only** deliverables collapse into one row per
format (e.g. "HTML · 5 deliverables", hours/value summed), so a format-only row means the name wasn't
posted, not that Cowork missed it. The "by format" table on *Impact & Value* stays a type/format rollup.

## Requirements

- Python 3. The whole default pipeline (`resolve_channel.py`, `parse_posts.py`, `build_dashboard.py`,
  `verify_dashboard.py`, `build_outputs.py`) is **standard library only** — the how-to-read guide is rendered inside the
  dashboard, so no extra dependency is needed. The **legacy** `build_guide_pdf.py` uses **reportlab**
  (pre-installed in the Copilot Cowork container) and only runs if you pass `--with-pdf`.
- Runs inside Microsoft Copilot Cowork (Teams + email tools provided by the host). The scripts
  themselves run anywhere Python 3 does.

## License

Add your license of choice (e.g. MIT) before publishing externally.

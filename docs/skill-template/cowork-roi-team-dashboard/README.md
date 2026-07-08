# Cowork ROI — Team Dashboard

A Microsoft Copilot **Cowork skill** that rolls up a small team's Copilot Cowork ROI. It reads the
de-identified stats each teammate posts to a shared Teams channel and renders **one self-contained,
anonymized HTML dashboard** the manager can open, re-price with a live hourly-rate control, and print.
It then **emails the channel members** a high-level summary with the dashboard and a **one-page
landscape PDF** that explains how to read it. On first run it **asks for the Teams channel link** and
remembers it; every run reads the **latest 15 days** of posts, keeping the latest post per person.

> **Team-safe by design.** Numbers only — no names, no file names, no country. Nothing is shown at an
> individual level; a Role breaks out only when at least **3** contributors share it.

## The three-skill family

| Skill | Role | Output |
|---|---|---|
| `cowork-roi-report` | A person's **full** personal impact report | Rich HTML web app (their own view) |
| `cowork-roi-member` | A person posts their **de-identified** stats to the team channel | HTML tables in Teams |
| **`cowork-roi-team-dashboard`** (this) | The **manager** aggregates everyone's posts | Anonymized team HTML dashboard + one-page PDF guide, emailed to the channel members |

This skill **only consumes** what `cowork-roi-member` posts. It does not harvest OneDrive and never
sees identities.

## Scope (v1)

Small, **homogeneous** teams (people doing similar work) at the **team level** — a handful of
contributors on one channel. Org-wide / large-team / multi-channel aggregation is intentionally out
of scope for now.

## Data flow

```
first run: user pastes channel link ──(scripts/resolve_channel.py)──▶  team_id + channel_id  ──▶ config

teammates ──(cowork-roi-member)──▶  Teams channel  ──(ListChannelMessages)──▶  raw_messages.json
                                                                                     │
                                                              scripts/parse_posts.py │  (last 15 days,
                                                              + process_groups.json  │   latest per sender,
                                                              + skills_vocabulary    │   group processes,
                                                              + skill_aliases         ▼   anonymize → role only)
                                                                                team_data.json
                                                                          ┌──────────┴───────────┐
                                       scripts/build_dashboard.py         │                      │  scripts/build_guide_pdf.py
                                       (k-anonymity, live rate)           ▼                      ▼  (reportlab, landscape)
                              output/cowork-team-roi-dashboard.html               output/how-to-read-team-roi-dashboard.pdf
                                                                          └──────────┬───────────┘
                                                          SendEmailWithAttachments ──▶ channel members
                                                          (high-level summary + both files attached)
```

## Quick start

1. **Point it at the channel** (first run only). The skill asks for the **link of the Teams channel**
   where the team posts its Cowork ROI stats (in Teams: channel ⋯ → *Get link to channel*), then
   resolves + saves the IDs:
   ```bash
   python scripts/resolve_channel.py --link "<pasted channel url>" --config config/team_config.json
   ```
   The Team must already exist and you must be a member. The channel **must match** the one
   `cowork-roi-member` posts to. (See `SKILL.md → First run`.)
2. **Read + build (last 15 days) + guide:**
   ```bash
   # after saving the channel messages' `value` array to working/raw_messages.json
   python scripts/parse_posts.py --in working/raw_messages.json \
          --config config/team_config.json --out working/team_data.json --window-days 15
   python scripts/build_dashboard.py --in working/team_data.json \
          --out output/cowork-team-roi-dashboard.html
   python scripts/build_guide_pdf.py --out output/how-to-read-team-roi-dashboard.pdf \
          --data working/team_data.json --config config/team_config.json
   ```
3. Open `output/cowork-team-roi-dashboard.html`; the skill emails both files to the channel members.

### Try it offline (no Teams needed)

Two real, de-identified posts are bundled:

```bash
python scripts/parse_posts.py --in examples/sample_raw_messages.json \
       --config config/team_config.json --out working/team_data.json \
       --window-days 15 --now 2026-07-02 --generated 2026-07-01
python scripts/build_dashboard.py --in working/team_data.json \
       --out output/cowork-team-roi-dashboard.html
python scripts/build_guide_pdf.py --out output/how-to-read-team-roi-dashboard.pdf \
       --data working/team_data.json --config config/team_config.json
```

## Config (`config/team_config.json`)

| Key | Meaning |
|---|---|
| `team_id`, `channel_id` | Where to read (authoritative). **Blank until first run**, then filled by `resolve_channel.py` from the pasted link. |
| `channel_link` | The Teams channel URL the user pasted on first run (kept for reference). |
| `hourly_rate` | Default $/hr for the value = hours × rate model (adjust live in the UI). |
| `cadence_days` | Posting/refresh cadence (default 14). |
| `message_lookback_days` | Window each run reads — **default 15** (the latest cycle). Enforced by `--window-days`. |
| `privacy_k_threshold` | Minimum contributors sharing an attribute before it breaks out (default 3). |
| `email_on_run` | When true (default), email the channel members the dashboard + PDF guide after building. |
| `team_size` | Optional; v1 shows a contributor count, not adoption %. |

## Privacy model

- Members are **counts + a number**, never named.
- The only attribute is the directory **Role** a post carries — never country, files, or prompts.
- **k-anonymity:** per-Role breakdowns require ≥ `privacy_k_threshold` contributors; otherwise they
  collapse into one combined bar. Small teams typically show a single combined bar.

## Shared taxonomy contract (keep in sync)

`process_groups.json`, `skills_vocabulary.json`, `roles_taxonomy.json`, and
`references/value-pillars.md` are **byte-for-byte mirrors** of the `cowork-roi-member` bundle (which
in turn mirrors `cowork-roi-report`). If those change, update this copy too or team aggregation
drifts. `skill_aliases.json` is reader-only and not part of the contract.

**Deliverable names:** the Member skill strips file names by design, so this dashboard shows
deliverables **by type**. Showing real names requires a Member-skill change (an opt-in name manifest)
first — see `SKILL.md → Cross-skill contract`.

## Requirements

- Python 3. The core pipeline (`resolve_channel.py`, `parse_posts.py`, `build_dashboard.py`) is
  **standard library only**. `build_guide_pdf.py` uses **reportlab** (pre-installed in the Copilot
  Cowork container) to render the one-page PDF guide.
- Runs inside Microsoft Copilot Cowork (Teams + email tools provided by the host). The scripts
  themselves run anywhere Python 3 (+ reportlab for the guide) does.

## License

Add your license of choice (e.g. MIT) before publishing externally.

# Cowork Team Report — Member v26

Shared capture fix with `cowork-roi-report` v42. This release repairs forward capture and documents
an opt-in historical backfill; it does not run a harvest, report, post, or schedule.

## Fixed
- `scripts/mine_session.py` discovers the newest current Copilot
  `/mnt/workspace/.copilot-state/*/session-state/*/events.jsonl`, while retaining both legacy
  transcript search patterns and the unchanged `--transcript`, `--out`, and `--log` options.
- Parse current session ids (parent-directory fallback), timestamps from every event, user and
  assistant messages, actual tool starts, and output artifacts from shutdown changes and host
  artifact-tool arguments. The first user-message line supplies an at-most-80-character title,
  with attachment and current-date tags removed. Duration remains elapsed wall-clock, not active time.
- Normalize `server-Tool` names to legacy MCP names before category, app, and source matching;
  include current code-edit, research, Teams, Outlook, calendar and transcript tools. Requested
  tools and completed tools do not double-count starts. Legacy Claude JSONL still parses.
- Current events use transcript artifact evidence, not unrelated existing workspace output files.
  Working/user-surface artifact writes and recursive folder destinations are not deliverable files.
- Correct the installed script-path guidance. The shared user settings now point the Stop and
  statusLine commands to `/mnt/user-config/skills/cowork-roi-report/scripts/`, leaving the telemetry
  log path `/mnt/user-config/.claude/cowork-session-telemetry.json` unchanged.

## Added
- SKILL.md §3b: ask once before enumerating the signed-in Cowork app's session list; read only
  titles and dates, never conversations or prompts. Add unmatched historical sessions with
  `has_folder:false`, `backfilled:true`, empty inputs/outputs, and no fabricated evidence or timing.
- All backfilled sessions pass through the existing §4 privacy picker before classification or
  computation. Declined/unavailable/incomplete browser access is disclosed in the post preview.
- First-run hook-configuration check in SKILL.md and README. OneDrive artifact harvesting and the
  forward-only log cannot recover historical chat-only sessions; fixing paths is not proof of
  automatic hook execution.

## Unchanged
Taxonomy, channel memory, telemetry and credits records, classifier/compute methodology, and the
privacy/posting gates are not modified by this update. Historical sessions are not recovered until
the user explicitly opts into a later backfill.

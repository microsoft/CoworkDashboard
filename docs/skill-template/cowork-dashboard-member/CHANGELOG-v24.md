# CHANGELOG — v24 (aligned with cowork-roi-report v24)

## Per-user taxonomy memory (privacy fix) — stop cross-user leakage

**Fatal flaw fixed:** the taxonomy memory could leak one user's personal jobs/processes into another
user. A teammate who dropped in the shared `cowork-dashboard-member/` folder and ran it got back *exactly*
the original user's processes and JTBDs instead of their own. This bundle is the one designed to be
copied between teammates, so it was the primary vector.

### What leaked (now removed from this bundle)
- **`cowork-process-registry.seed.json`** shipped with real process names + JTBDs, and first-run copied
  it into the new user's registry. **The seed is deleted — no seed ships. First run starts with no
  memory** and mints processes from the user's OWN sessions.
- **`scripts/process_overrides.json`** shipped **populated** with real session→process mappings (the
  docs falsely claimed "ships empty"); `classify.py` read it directly. **Reset to `{}`.**

### The fix
- **Owner-scoped, per-user registry** at `/mnt/user-config/.claude/cowork-process-registry.<userkey>.json`
  (`<userkey>` derives from the invoking user's email), carrying an `owner` field. It lives on the
  user's own mount and syncs to **their** OneDrive `Documents/Cowork/` folder — the memory is in the
  user's Cowork folder and is theirs alone.
- **Identity guard.** `reconcile_taxonomy.py` **ignores any registry whose `owner` isn't the invoking
  user** (leaked / inherited / unstamped) and starts empty, so a leaked file can never contaminate
  another user. New `--owner` arg (falls back to the harvested `meta.email`); refuses to write an
  unscoped registry.
- **Per-run scratch out of the bundle.** `reconcile_taxonomy.py` writes `working/process_overrides.json`;
  `classify.py` reads it via `--overrides`. Personal per-run data never lands in `scripts/` again.
- `GetMyDetails` now also selects `userPrincipalName`.
- **Packaging guardrail** added to `SKILL.md` / `README.md`: never bundle the registry, any
  `cowork-process-registry*.json`, or a populated `process_overrides.json`; overrides ship as `{}`.

### Migration
Existing users keep their memory: the old unscoped `cowork-process-registry.json` is copied to the
owner-scoped filename with an `owner` stamp before the first v24 run (the guard ignores the unstamped
file, so migrate first).

### Unchanged
The de-identified table post (headline, categories, pillars, JTBDs, processes, roles, skills,
analyzed→produced, deliverables, activity), the mandatory privacy opt-out, the fixed team
channel, and the research-anchored two-clock methodology — all as before. Alignment logic is
byte-for-byte identical to the report skill; only the registry location, owner guard, and overrides
path changed.

#!/usr/bin/env python3
"""
resolve_channel.py — turn a pasted Microsoft Teams CHANNEL (or channel-message) link into the
team_id + channel_id this skill reads, and persist them into config/team_config.json.

Runs on the FIRST use of the skill (when the config has no channel yet). The skill asks the user
to paste the link of the Teams channel where teammates post their Cowork ROI stats; this script
extracts the IDs deterministically from that URL — no Graph call needed — and writes them back so
every later run reads the exact same place.

A Teams channel link looks like:
  https://teams.microsoft.com/l/channel/19%3Axxxxxxxx%40thread.tacv2/General?groupId=<TEAM-GUID>&tenantId=<...>
A channel message link looks like:
  https://teams.microsoft.com/l/message/19%3Axxxxxxxx%40thread.tacv2/1234567890?groupId=<TEAM-GUID>&...
Both carry the channel thread id in the path and the team id in the `groupId` query parameter.

Usage:
  python resolve_channel.py --link "<pasted url>" --config config/team_config.json
  python resolve_channel.py --link "<pasted url>" --config config/team_config.json --json
"""
import argparse, json, os, re, sys
from urllib.parse import unquote, urlparse, parse_qs

THREAD_RE = re.compile(r"(19:[^/?#]+?@thread\.[a-z0-9]+)", re.I)
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def resolve(link):
    """Return (team_id, channel_id, channel_name) parsed from a Teams channel/message link."""
    raw = (link or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("empty link")
    decoded = unquote(raw)

    # channel_id: the 19:...@thread.xxx segment (works decoded or not)
    m = THREAD_RE.search(decoded) or THREAD_RE.search(raw)
    channel_id = m.group(1) if m else ""

    # team_id: the groupId query parameter
    q = parse_qs(urlparse(raw).query)
    team_id = (q.get("groupId") or q.get("groupid") or [""])[0]
    if not team_id:
        m2 = re.search(r"groupId=([0-9a-f-]{36})", decoded, re.I)
        team_id = m2.group(1) if m2 else ""

    # channel_name: the path segment right after the thread id (best-effort, cosmetic only)
    channel_name = ""
    path = urlparse(decoded).path
    parts = [p for p in path.split("/") if p]
    for i, p in enumerate(parts):
        if THREAD_RE.match(p) and i + 1 < len(parts):
            cand = parts[i + 1]
            if not cand.isdigit():          # a message id is all digits — skip it
                channel_name = cand
            break

    if not channel_id or "@thread." not in channel_id:
        raise ValueError("could not find a channel thread id (19:...@thread....) in the link")
    if not GUID_RE.match(team_id):
        raise ValueError("could not find a team id (groupId=<guid>) in the link")
    return team_id, channel_id, channel_name


def main(a):
    team_id, channel_id, channel_name = resolve(a.link)

    cfg = {}
    if os.path.exists(a.config):
        with open(a.config, encoding="utf-8") as f:
            cfg = json.load(f)

    cfg["team_id"] = team_id
    cfg["channel_id"] = channel_id
    cfg["channel_link"] = (a.link or "").strip().strip('"').strip("'")
    if channel_name and not cfg.get("channel_name"):
        cfg["channel_name"] = channel_name

    with open(a.config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")

    out = {"team_id": team_id, "channel_id": channel_id, "channel_name": cfg.get("channel_name", "")}
    if a.json:
        print(json.dumps(out))
    else:
        print(f"[resolve_channel] team_id={team_id}")
        print(f"[resolve_channel] channel_id={channel_id}")
        print(f"[resolve_channel] wrote {a.config}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--link", required=True, help="Pasted Teams channel or channel-message URL")
    ap.add_argument("--config", default="config/team_config.json")
    ap.add_argument("--json", action="store_true")
    try:
        main(ap.parse_args())
    except ValueError as e:
        print(f"[resolve_channel] ERROR: {e}", file=sys.stderr)
        sys.exit(2)

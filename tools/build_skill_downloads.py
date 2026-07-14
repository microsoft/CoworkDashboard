#!/usr/bin/env python3
"""
build_skill_downloads.py — package the canonical skill source folders into the zips the
Installer Studio serves, so the downloads never drift from the maintained source.

For each skill it writes TWO identical zips (same bytes/layout):
  * docs/downloads/<slug>.zip          — served by the Installer Studio web app
  * <root skill folder>/<slug>.zip     — the convenience copy that sits next to the source

The zip root is the skill folder itself (e.g. `cowork-dashboard-member/...`) so Cowork imports
it as a skill. Entry names always use forward slashes so the archive works on macOS/OneDrive too.

Safety rails:
  * The skill files are copied byte-for-byte from the source folder — nothing is edited here.
  * The channel config that ships MUST be blank (the app fills it at download time, and a manual
    download is meant to prompt on first run). The build ABORTS if a populated config is found,
    so a real team's channel can never be committed by accident.

Usage:  python tools/build_skill_downloads.py
"""
import json
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# slug -> (root skill folder that holds it, channel config path within the skill, channel field names)
SKILLS = {
    "cowork-dashboard-member": {
        "root": "Cowork Dashboard - Team Member Cowork Skill",
        "config": "config/team_channel.json",
        "channel_fields": ["channel_link", "team_id", "channel_id", "channel_name"],
    },
    "cowork-dashboard-team-dashboard": {
        "root": "Cowork Dashboard - Team Dashboard Cowork Skill",
        "config": "config/team_config.json",
        "channel_fields": ["channel_link", "team_id", "channel_id", "channel_name"],
    },
}


def fail(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def assert_blank_config(skill_dir, cfg_rel, fields):
    cfg_path = os.path.join(skill_dir, *cfg_rel.split("/"))
    if not os.path.exists(cfg_path):
        fail("missing channel config: " + cfg_path)
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    populated = [k for k in fields if str(cfg.get(k, "")).strip()]
    if populated:
        fail("refusing to package a populated channel config (%s): %s" % (cfg_rel, ", ".join(populated)))


def collect_files(skill_dir):
    out = []
    for base, _dirs, files in os.walk(skill_dir):
        for fn in files:
            full = os.path.join(base, fn)
            rel = os.path.relpath(full, skill_dir).replace(os.sep, "/")
            out.append((full, rel))
    return sorted(out, key=lambda x: x[1])


def build_zip(dest, slug, files):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        os.remove(dest)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in files:
            z.write(full, slug + "/" + rel)


def main():
    downloads = os.path.join(REPO, "docs", "downloads")

    # Remove any stale, differently-named download zips so only the canonical set remains.
    if os.path.isdir(downloads):
        for fn in os.listdir(downloads):
            if fn.endswith(".zip") and fn[:-4] not in SKILLS:
                os.remove(os.path.join(downloads, fn))
                print("removed stale download: " + fn)

    for slug, meta in SKILLS.items():
        skill_dir = os.path.join(REPO, meta["root"], slug)
        if not os.path.isdir(skill_dir):
            fail("missing skill source folder: " + skill_dir)
        assert_blank_config(skill_dir, meta["config"], meta["channel_fields"])
        files = collect_files(skill_dir)

        served = os.path.join(downloads, slug + ".zip")
        convenience = os.path.join(REPO, meta["root"], slug + ".zip")
        build_zip(served, slug, files)
        build_zip(convenience, slug, files)
        print("built %s (%d files) -> docs/downloads/%s.zip + root copy" % (slug, len(files), slug))


if __name__ == "__main__":
    main()

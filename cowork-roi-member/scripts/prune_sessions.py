#!/usr/bin/env python3
"""
prune_sessions.py — privacy opt-out helper for the Cowork ROI member skill.

Two modes, both operating on the harvested working/cowork_raw.json (the canonical
pre-compute session list):

  --list            Print a numbered inventory (index · date · goal) of every
                    harvested session, so the user can see exactly what would be
                    counted and choose which chats/tasks to leave OUT of the report.
                    A machine-stable block is printed between INDEX markers.

  --drop "1,4,9"    Remove the 1-based indices the user selected (as shown by --list)
  --drop-ids "a,b"  Remove specific session ids
                    Either writes back in place (default) or to --out. Prints what was
                    removed and what remains.

This runs BEFORE classify.py/compute.py, so excluded sessions never reach the
metrics or the posted message — nothing about them is computed, named, or sent.

Usage:
  python prune_sessions.py --in working/cowork_raw.json --list
  python prune_sessions.py --in working/cowork_raw.json --drop "3,11,27"
"""
import json, argparse, sys

LIST_B = "<<<COWORK-SESSION-INVENTORY>>>"
LIST_E = "<<<END-INVENTORY>>>"


def load(p):
    return json.load(open(p))


def do_list(d):
    sessions = d.get("sessions", [])
    print(LIST_B)
    for i, s in enumerate(sessions, 1):
        date = s.get("date", "?")
        goal = s.get("goal", "(untitled session)")
        n_out = len(s.get("outputs", []) or [])
        kind = f"{n_out} deliverable{'s' if n_out != 1 else ''}" if n_out else "chat only"
        print(f"[{i:>2}] {date} · {goal}  ({kind})")
    print(LIST_E)
    print(f"\n[{len(sessions)} sessions total]")
    # Privacy nudge — shown every time the inventory is listed, so it reaches the
    # user right where they choose what to leave out.
    print("\nReminder: this posts to your team channel. Exclude anything personal "
          "or non-work you're not comfortable sharing before it posts — each "
          "session's deliverables go out with it.")


def do_drop(d, drop_idx, drop_ids, inp, out):
    sessions = d.get("sessions", [])
    n = len(sessions)
    idx = set()
    for tok in (drop_idx or "").replace(" ", "").split(","):
        if tok.isdigit():
            idx.add(int(tok))
    ids = {x.strip() for x in (drop_ids or "").split(",") if x.strip()}

    kept, removed = [], []
    for i, s in enumerate(sessions, 1):
        if i in idx or s.get("id") in ids:
            removed.append(s)
        else:
            kept.append(s)

    d["sessions"] = kept

    # An excluded session's deliverables ride inside its own `outputs`, so dropping
    # the session drops them too. Count them explicitly so the guarantee is visible,
    # and — belt-and-braces — also strip any excluded session's entries from a
    # parallel top-level deliverable/artifact array if a harvest ever writes one,
    # keyed by the removed sessions' ids.
    removed_ids = {s.get("id") for s in removed if s.get("id")}
    deliv_removed = sum(len(s.get("outputs", []) or []) for s in removed)
    orphans_stripped = 0
    for arr_key in ("deliverables", "artifacts", "outputs"):
        arr = d.get(arr_key)
        if isinstance(arr, list):
            before = len(arr)
            d[arr_key] = [x for x in arr
                          if not (isinstance(x, dict)
                                  and (x.get("session") in removed_ids
                                       or x.get("id") in removed_ids))]
            orphans_stripped += before - len(d[arr_key])

    json.dump(d, open(out, "w"), indent=1)
    print(f"Removed {len(removed)} of {n} session(s); {len(kept)} remain.")
    for s in removed:
        n_out = len(s.get("outputs", []) or [])
        print(f"  - excluded: {s.get('date','?')} · {s.get('goal','(untitled)')} "
              f"(+{n_out} deliverable{'s' if n_out != 1 else ''})")
    print(f"Deliverables removed with those sessions: {deliv_removed}"
          + (f" (+{orphans_stripped} orphaned top-level entries)" if orphans_stripped else ""))

    # Verify: no kept session, and no surviving top-level deliverable entry, points
    # at an excluded session.
    leaks = [x for k in ("deliverables", "artifacts", "outputs")
             for x in (d.get(k) or []) if isinstance(x, dict)
             and (x.get("session") in removed_ids or x.get("id") in removed_ids)]
    assert not leaks, f"prune verification failed: {len(leaks)} deliverable(s) still reference an excluded session"
    print(f"Verified: no remaining deliverable references an excluded session.")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="working/cowork_raw.json")
    ap.add_argument("--out", default=None, help="defaults to --in (in place)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--drop", default="", help="comma list of 1-based indices from --list")
    ap.add_argument("--drop-ids", dest="drop_ids", default="", help="comma list of session ids")
    a = ap.parse_args()
    d = load(a.inp)
    if a.list:
        do_list(d)
    elif a.drop or a.drop_ids:
        do_drop(d, a.drop, a.drop_ids, a.inp, a.out or a.inp)
    else:
        print("Nothing to do — pass --list or --drop/--drop-ids.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

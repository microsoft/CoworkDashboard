#!/usr/bin/env python3
"""
make_invite.py — render an INVITING "get started" message the manager posts into the
team's Cowork report channel, so members are onboarded in-place instead of being handed
a bare .zip with no context.

It renders the same invite three ways and prints each between stable markers so the
calling agent can lift them verbatim:

  * a Teams channel post  (HTML)  -> post with PostChannelMessage + pin it
  * an email body         (HTML)  -> optionally SendEmailWithAttachments to channel members
  * a short plaintext blurb        -> for a chat/DM or release notes
  * a personalized 1:1 DM  (HTML)  -> direct-message each teammate (pass --recipient-name)

The message tells the member WHAT this is, WHY it helps them, the PRIVACY promise, and
the 1-2-3 of WHAT TO DO — with the download link baked in. stdlib only.

Usage:
  python scripts/make_invite.py --team-name "Data & AI" \
      --download-url "https://.../cowork-dashboard-member.zip" \
      [--channel-link "https://teams.microsoft.com/l/channel/..."] \
      [--cadence "every other Monday"] [--recipient-name "Alex"] [--out-dir working]
"""
import argparse
import html
import os
import sys

POST_B, POST_E = "<<<MEMBER-INVITE-CHANNEL-POST>>>", "<<<END-CHANNEL-POST>>>"
MAIL_S_B, MAIL_S_E = "<<<MEMBER-INVITE-EMAIL-SUBJECT>>>", "<<<END-EMAIL-SUBJECT>>>"
MAIL_B, MAIL_E = "<<<MEMBER-INVITE-EMAIL-BODY>>>", "<<<END-EMAIL-BODY>>>"
TEXT_B, TEXT_E = "<<<MEMBER-INVITE-PLAINTEXT>>>", "<<<END-PLAINTEXT>>>"
DM_B, DM_E = "<<<MEMBER-INVITE-DM>>>", "<<<END-DM>>>"

RUN_PHRASE = "run the Cowork Team Report member step"


def _steps_html(url):
    dl = html.escape(url) if url else ""
    step1 = ('<b>Install it</b> — download the skill'
             + (f' (<a href="{dl}">{dl}</a>)' if dl else ' from the link your manager shared')
             + ' and drop the <code>cowork-dashboard-member</code> folder into your Copilot Cowork '
               'skills folder.')
    return (
        "<ol style='margin:6px 0 0 18px;padding:0'>"
        f"<li style='margin:4px 0'>{step1}</li>"
        f"<li style='margin:4px 0'><b>Run it</b> — in Copilot Cowork, say "
        f"&ldquo;<i>{html.escape(RUN_PHRASE)}</i>&rdquo;.</li>"
        "<li style='margin:4px 0'><b>Review &amp; confirm</b> — it lists your Cowork sessions; "
        "untick anything you&rsquo;d rather not share, then it posts your <b>de-identified</b> "
        "stats right here — aggregate numbers and de-identified descriptions only.</li>"
        "</ol>")


def render_post(team, url, cadence):
    team_bit = f" for {html.escape(team)}" if team else ""
    return (
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#242424;"
        "max-width:640px'>"
        f"<p style='font-size:16px;margin:0 0 6px'>👋 <b>Welcome to our Cowork impact channel"
        f"{team_bit}</b></p>"
        "<p style='margin:0 0 10px'>This channel adds up how <b>Copilot Cowork</b> is helping our "
        "team — the hours it saves, the work it accelerates, the value it creates. You contribute in "
        "about <b>two minutes</b> with a small skill that turns <i>your own</i> Cowork work into a "
        "<b>privacy-safe</b> summary and posts it here.</p>"
        "<p style='margin:0 0 4px'><b>Why bother?</b> Your wins get counted in the team story, and "
        "leadership sees our <i>collective</i> ROI — never who did what.</p>"
        "<p style='margin:0 0 4px'><b>Your privacy is protected.</b> Personal names, prompts, and raw "
        "file names are stripped — your work is shared only as <b>de-identified descriptions</b> and "
        "aggregate stats, never who did what. You see every session first and can exclude any of it "
        "before anything posts.</p>"
        "<p style='margin:10px 0 2px'><b>Get started (one time):</b></p>"
        f"{_steps_html(url)}"
        f"<p style='margin:10px 0 0;color:#616161;font-size:12.5px'>Takes ~2 min · runs on demand or "
        f"automatically <b>{html.escape(cadence)}</b> · questions? just reply here.</p>"
        "</div>")


def render_email(team, url, cadence):
    # Email reuses the post body with a short lead-in line.
    lead = ("<p style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#242424'>"
            "You&rsquo;re invited to add your Copilot Cowork impact to our team&rsquo;s "
            "(private, de-identified) rollup. Here&rsquo;s what it is and how to start:</p>")
    return lead + render_post(team, url, cadence)


def render_text(team, url, cadence):
    t = f" for {team}" if team else ""
    dl = url or "(link your manager shared)"
    return (
        f"Welcome to our Copilot Cowork impact channel{t}!\n"
        "In ~2 minutes you can add your own Cowork work to our team's privacy-safe ROI rollup — "
        "personal names, prompts, and raw file names are stripped (work is shown as de-identified "
        "descriptions and aggregate stats), and you review/exclude sessions first.\n"
        "Get started (one time):\n"
        f"  1. Install: download {dl} and drop the cowork-dashboard-member folder into your "
        "Copilot Cowork skills folder.\n"
        f"  2. Run: in Cowork, say \"{RUN_PHRASE}\".\n"
        "  3. Review the session list, exclude anything private, and it posts your de-identified "
        "stats here.\n"
        f"Runs on demand or automatically {cadence}. Questions? Just reply here.")


def render_dm(team, url, cadence, name):
    # A warm, personal 1:1 chat message the manager DMs to each teammate.
    greet = f"Hi {html.escape(name.strip())}" if name and name.strip() else "Hi there"
    team_label = f" {html.escape(team)}" if team else ""
    return (
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#242424;"
        "max-width:600px'>"
        f"<p style='margin:0 0 10px'>{greet} 👋 — I&rsquo;ve set up a quick way for our{team_label} "
        "team to see how <b>Copilot Cowork</b> is helping us, and I&rsquo;d love for you to be "
        "part of it.</p>"
        "<p style='margin:0 0 10px'>It takes about <b>two minutes</b> and it&rsquo;s "
        "<b>privacy-safe</b>: personal names, prompts, and raw file names are stripped — your work is "
        "shared only as <b>de-identified descriptions</b> and aggregate stats, never who did what. You "
        "review and exclude any of your sessions before anything posts.</p>"
        "<p style='margin:10px 0 2px'><b>To join (one time):</b></p>"
        f"{_steps_html(url)}"
        f"<p style='margin:10px 0 0;color:#616161;font-size:12.5px'>Takes ~2 min · runs on demand or "
        f"automatically <b>{html.escape(cadence)}</b> · any questions, just message me back!</p>"
        "</div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team-name", default="")
    ap.add_argument("--download-url", default="")
    ap.add_argument("--channel-link", default="")
    ap.add_argument("--cadence", default="every other Monday")
    ap.add_argument("--recipient-name", default="",
                    help="First name for a personalized 1:1 DM greeting; blank = generic.")
    ap.add_argument("--out-dir", default="working")
    a = ap.parse_args()

    team = (a.team_name or "").strip()
    url = (a.download_url or "").strip()
    cadence = (a.cadence or "every other Monday").strip()

    post = render_post(team, url, cadence)
    subject = "Get started: add your Copilot Cowork impact to the team rollup" + (f" — {team}" if team else "")
    email = render_email(team, url, cadence)
    text = render_text(team, url, cadence)
    dm = render_dm(team, url, cadence, a.recipient_name)

    if not url:
        print("NOTE: no --download-url given — the invite tells members to use the link the manager "
              "shared. Pass --download-url for a one-click install.", file=sys.stderr)

    try:
        os.makedirs(a.out_dir, exist_ok=True)
        with open(os.path.join(a.out_dir, "member_invite_post.html"), "w", encoding="utf-8") as f:
            f.write(post)
        with open(os.path.join(a.out_dir, "member_invite_email.html"), "w", encoding="utf-8") as f:
            f.write(email)
    except OSError as e:
        print(f"WARN: could not write invite files: {e}", file=sys.stderr)

    for b, body, e in ((POST_B, post, POST_E),
                       (MAIL_S_B, subject, MAIL_S_E),
                       (MAIL_B, email, MAIL_E),
                       (TEXT_B, text, TEXT_E),
                       (DM_B, dm, DM_E)):
        print(b)
        print(body)
        print(e)


if __name__ == "__main__":
    main()

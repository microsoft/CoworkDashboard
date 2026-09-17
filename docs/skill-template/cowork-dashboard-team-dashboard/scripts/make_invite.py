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


def _invite_steps():
    return (
        "<ol style='margin:6px 0 0 18px;padding:0'>"
        "<li style='margin:4px 0'>Save this skill locally (the attached <code>.zip</code>).</li>"
        "<li style='margin:4px 0'>Open a Copilot Cowork session, click the <b>+</b> icon, and upload "
        "files and images.</li>"
        "<li style='margin:4px 0'>Install this skill.</li>"
        f"<li style='margin:4px 0'>Run this report — say &ldquo;<i>{html.escape(RUN_PHRASE)}</i>&rdquo;.</li>"
        "</ol>")


def _team_bit(team):
    return f" our {html.escape(team)} team&rsquo;s" if team else " our team&rsquo;s"


def _invite_html(intro, width=620):
    # Shared invite copy — the email, channel post, and 1:1 DM all read the same.
    return (
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#242424;"
        f"max-width:{width}px'>"
        f"{intro}"
        f"{_invite_steps()}"
        "<p style='margin:12px 0 0'>The skill gathers your <b>last 15 days</b> of Cowork activity and "
        "lets you <b>exclude sessions before sharing</b>. Looking forward to seeing some aggregate stats "
        "on how our team is benefiting from Cowork!</p>"
        "</div>")


def render_post(team, url, cadence):
    intro = ("<p style='margin:0 0 10px'>We&rsquo;re exploring how <b>Copilot Cowork</b> is assisting"
             f"{_team_bit(team)} workflow with a skill. Please attach this skill:</p>")
    return _invite_html(intro)


def render_email(team, url, cadence):
    # Email uses the same copy as the channel post / DM.
    return render_post(team, url, cadence)


def render_text(team, url, cadence):
    tb = f" our {team} team's" if team else " our team's"
    return (
        f"We're exploring how Copilot Cowork is assisting{tb} workflow with a skill. Please attach this skill:\n"
        "  1. Save this skill locally (the attached .zip).\n"
        "  2. Open a Copilot Cowork session, click the + icon, and upload files and images.\n"
        "  3. Install this skill.\n"
        f"  4. Run this report — say \"{RUN_PHRASE}\".\n"
        "The skill gathers your last 15 days of Cowork activity and lets you exclude sessions before "
        "sharing. Looking forward to seeing some aggregate stats on how our team is benefiting from Cowork!")


def render_dm(team, url, cadence, name):
    greet = f"Hi {html.escape(name.strip())} 👋 — " if name and name.strip() else "Hi there 👋 — "
    intro = (f"<p style='margin:0 0 10px'>{greet}we&rsquo;re exploring how <b>Copilot Cowork</b> is "
             f"assisting{_team_bit(team)} workflow with a skill. Please attach this skill:</p>")
    return _invite_html(intro, width=600)


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

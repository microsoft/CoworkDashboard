# Privacy statement — Cowork Team Report (Installer Studio & skills)

_Last updated: 2026-09-18_

This project is published by the **Microsoft Copilot Growth ROI Advisory Team**. It has two parts, and
**neither one operates a server or collects data on your behalf**. This statement explains exactly what
each part does with information.

## 1. The Installer Studio web page

The Installer Studio (`https://microsoft.github.io/CoworkDashboard/`) is a **static, client-side web
page** hosted on GitHub Pages. When you use it:

- **Everything runs in your browser.** The page loads static files (HTML, CSS, JavaScript, the
  [JSZip](https://stuk.github.io/jszip/) library, and the pre-built skill `.zip` files) from GitHub
  Pages and does all of its work locally on your device.
- **No data is sent to us or to any third party.** The page makes **no** third-party network calls, has
  **no** analytics, tracking pixels, advertising, or telemetry, and sets **no** cookies. There is no
  sign-in and we never ask for a password or any credential.
- **Your Teams channel link stays on your device.** When you paste your team's Teams channel link, the
  page parses it **entirely in the browser** to extract the `team_id`, `channel_id`, and channel name.
  That link is **never uploaded to any server.** It is written only into the configuration file *inside
  the `.zip` you download*, so the skill can skip its first-run "paste the link" prompt. Before writing
  it, the page validates that the input is an `https` Microsoft Teams link and rejects anything else.
- **Downloads are generated locally.** The skill `.zip` you download is assembled in your browser from
  the static template plus your channel value. Nothing about that download is reported back to us.

Because the page is fully client-side, we (the maintainers) receive **no** information about who visits
it, what link you paste, or what you download. Standard GitHub Pages hosting logs may apply as described
in the [GitHub Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-privacy-statement).

## 2. The Cowork skills (Team Member & Team Dashboard)

The downloaded skills run **inside your own Microsoft Copilot Cowork / Microsoft 365 environment**, under
your organization's existing Microsoft privacy, security, and compliance controls. They do not send data
to this project or to any third party.

- **Team Member skill** — summarizes *your own* Copilot Cowork activity into a **de-identified,
  team-level** report and posts it into the one shared Teams channel you point it at. Before publishing,
  you review the sessions included and can remove any you don't want counted; removed sessions and their
  work artifacts are never computed or posted. Posts do **not** reveal your name or raw file names.
- **Team Dashboard skill** — reads only the de-identified summaries teammates have already posted in that
  shared channel and combines them into one **anonymized, aggregate** dashboard. It never reads anyone's
  files, and it shows **nothing at an individual level** (a per-role breakdown appears only when enough
  people share a role, per the k-anonymity threshold in the skill).

The skills are **estimation and reporting tools**. The figures they produce are directional estimates of
tool-assisted time savings — not audited financials, and not individual or team performance scores.

## 3. Information we do **not** collect

- No names, credentials, passwords, or sign-in of any kind.
- No financial or payment information.
- No cookies, analytics, tracking, or advertising identifiers.
- No copy of your Teams channel link, your files, or your prompts.

## 4. Contact

Questions or requests about this statement:
**copilot-roi-advisory-team-gh@microsoft.com**

For Microsoft's general privacy practices, see the
[Microsoft Privacy Statement](https://privacy.microsoft.com/privacystatement).

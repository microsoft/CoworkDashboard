# Cowork Team Report — Team Member Cowork Skill

**Cowork Team Report** is a two-part Microsoft Copilot **Cowork** solution that shows a team the **ROI**
they're getting from Copilot — the hours saved and the dollar value of that time — and turns it into a tidy
report that lands in everyone's inbox. It's made of two skills that work together through **one shared
Teams channel**:

- **Cowork Team Report — Team Member skill**. Every teammate runs it on their own work. It turns
  their Copilot Cowork activity into a clear, de-identified summary — hours saved, the value of that time,
  the kinds of work Copilot helped with, and what they produced — and emails it as easy-to-read tables to
  the shared channel's email address. Before sending, each person reviews the sessions included and can
  remove any they do not want in the report; removed sessions and their work artifacts are never computed
  or sent. The email does not reveal the person's name or raw filenames, but retained work artifacts may
  be shown under de-identified descriptive names so the team can understand what was produced.
- **Cowork Team Report — Team Dashboard skill** (the manager skill). The manager/lead runs it. It reads the shared
  channel, combines everyone's summaries into one anonymized HTML dashboard, and **emails the team a
  newsletter** (the dashboard, with the how-to-read guide built in) on a schedule the manager chooses. It only ever reads
  what teammates email into the channel — never anyone's files.

<p align="center">
  <a href="https://microsoft.github.io/CoworkDashboard/demo-report.html?v=2"><img src="images/team-dashboard-demo.gif?v=1" alt="Animated preview of the Cowork Team Dashboard — cycling through the Overview, Impact & Value, and How Cowork is used tabs (sample data)" width="760" /></a>
</p>
<p align="center"><sub><b>What the team gets:</b> one anonymized, team-level ROI dashboard — Overview, Impact &amp; Value and How Cowork is used tabs (sample data shown). <a href="https://microsoft.github.io/CoworkDashboard/demo-report.html?v=2">Open the live interactive demo ↗</a></sub></p>

To make rollout effortless, this repository also hosts a small web page — the
**[Installer Studio](https://aka.ms/CoworkDashboard)** — where a
manager adds their team's channel link and email address, then downloads **both** skills with the required
channel details already built in. Nobody is asked to choose a report recipient. The rest of this guide walks a manager through the whole
process.

<p align="center">
  <a href="https://aka.ms/CoworkDashboard"><img src="images/Installer_Studio_Screenshot.png?v=3" alt="The Installer Studio page (top half) — add your Teams channel details" width="380" align="top" /></a>
  <a href="https://aka.ms/CoworkDashboard"><img src="images/Installer_Studio_Screenshot_2.png?v=3" alt="The Installer Studio page (bottom half) — download both skills, ready to install" width="380" align="top" /></a>
</p>

## 🎬 Watch First

Plays here in the page — no download. A step-by-step setup walkthrough: how the team leader stands up the Cowork Team Report, how teammates run the member skill, and what the Team Dashboard shows once it's running.

https://github.com/user-attachments/assets/f020831d-cb38-423f-b647-ce4415ae7f44

▶️ **[Watch the setup walkthrough](media/Team-Cowork-Skill-Overview.mp4)** &nbsp;·&nbsp; captions: [`.srt`](media/Team-Cowork-Skill-Overview.srt)

## What you'll need first

A **Teams channel with email enabled** where your team's Cowork reports will be collected — for example
`Cowork report - {your team name}`. If you don't have one yet, create it in Microsoft Teams before you
start, add the people whose work you want included, and allow those members in the channel's email
security settings. Keep the channel just for these reports.

## Set it up — step by step

You only do this **once** for your team.

1. **Open the Installer Studio page** in your web browser:
   https://aka.ms/CoworkDashboard

2. **Copy your team's Teams channel link and email address.** In Microsoft Teams, find the channel in the left-hand list,
   hover over its name, and click the **⋯ More options** button that appears (or right-click the channel).
   Choose **Copy link** (some Teams versions label it **Get link to channel**) and then
   **Get email address**. Configure the email security settings to allow the members who will send reports.

3. **Paste both values** into the page and click **Build my install links.** The page validates the link
   and email address and shows the **channel name** it found — check it's the right channel.

4. **Download both skills.** Two buttons appear, each already carrying your channel:
   - **Download the manager skill (.zip)** — you install this one.
   - **Download the team-member skill (.zip)** — you send this one to your team.

5. **Install the manager skill (that's you) — and let it set you up.** Open **Copilot Cowork**, upload the
   *manager* zip **(upload the `.zip` file as-is — don't unzip it first)**, and ask it to install **and walk
   you through setup** (for example: *“install this manager skill, then walk me through setup — starting with
   sending the member skill to my team”*). That second half matters: installing a skill on its own runs
   nothing, so it makes the skill immediately offer to send the member skill to your teammates — the step
   that actually makes the dashboard fill up. Because your channel is already built in, it won't ask you for a
   link. Afterwards you can say *“build the team Cowork Team Report”* any time — or ask it to run on a
   schedule and email the team automatically.

6. **Share the team-member skill with your team.** Send the *team-member* zip to everyone whose Copilot work
   you'd like included. Each person uploads it in Copilot Cowork **(the `.zip` file as-is — don't unzip it
   first)** and asks it to install the skill — the same simple step. After each mandatory privacy
   review, their report is emailed to the channel address already in the skill; no one chooses a recipient.

That's the whole setup. From here on, teammates email their summaries into the channel and your manager skill rolls them up
into the emailed newsletter — refreshing on its schedule with nothing more for you to do.

### What teammates control before publishing

Every teammate gets a privacy review before a report is emailed to the channel. They can remove any session
they do not want included; removing a session also removes all work artifacts associated with it. This only
removes the session from the pending report — it does not delete the original Cowork session.

Sent reports do not reveal the contributor's individual identity, prompts, or raw filenames. They can
name retained work artifacts using de-identified descriptive labels, along with details such as artifact type,
business process, skills, hours, and value. Teammates should remove any session whose artifact descriptions
they are not comfortable sharing with the channel.

> **Want your own Copilot work counted too?** As the manager you can *also* install the team-member skill on
> your own Copilot — that's optional, and only needed if you want your own stats in the team totals.

## What the downloads contain

Each Installer Studio download is an ordinary copy of the matching skill with **the channel detail it needs
already filled in**, so it works the moment it's installed. The member config receives the Teams channel
email address; the manager config receives the channel link and IDs. Nothing else about either skill is changed.
A plain, unconfigured member copy cannot send until an admin populates `channel_email`; it never guesses or asks
the member to choose a recipient. A plain manager copy asks for the channel link on first run.

## Are my channel details private?

Yes. The link and email address you paste stay entirely inside your own web browser. They are never
sent to a server, and the page makes no outside network calls — it only builds the downloads locally.

---

## Two ways to get the skills

- **A — Installer Studio (recommended).** Paste your channel link and email address on the
  [page above](https://aka.ms/CoworkDashboard) and download the two zips. Each skill gets the channel
  detail it needs, so you and your team just upload each zip and run it.
- **B — Grab the zips straight from this repo (manual).** The un-baked skill zips live next to each skill folder
  and under [`docs/downloads/`](docs/downloads/). These ship with a **blank** channel, so the first time each
  manager skill asks for the Teams channel link on first run. Before distributing a manual member
  copy, an admin must populate `config/team_channel.json` with the Teams channel email address.

Both paths install the exact same skill code — path A only pre-fills the channel config so there's no first-run
question.

## Prefer to install by hand?

You don't have to let Copilot unpack the zip for you — you can drop the skill into place yourself:

1. **Get a skill zip** — either from the [Installer Studio](https://aka.ms/CoworkDashboard) page (channel details baked in)
   or straight from this repo (blank config, see option B above) — and **unzip** it. You'll get a single folder,
   either `cowork-dashboard-member/` (the team-member skill) or `cowork-dashboard-team-dashboard/` (the manager skill).
2. **Copy that folder** into your Cowork skills directory (use the line that matches the skill you're
   installing):
   ```
   Documents/Cowork/skills/cowork-dashboard-member/
   Documents/Cowork/skills/cowork-dashboard-team-dashboard/
   ```
3. Wait about 35 seconds for OneDrive to sync, and the skill is ready to use in Copilot Cowork.

If you used an Installer Studio download, the required channel details are already baked in.
If you used a blank member copy from this repo, populate its `channel_email` before installing it.
The blank manager copy asks for the Teams channel link on first run.

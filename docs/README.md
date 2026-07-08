# Cowork ROI — Team Member Cowork Skill

**Cowork ROI** is a two-part Microsoft Copilot **Cowork** solution that shows a team the value they're
getting from Copilot — and turns it into a tidy report that lands in everyone's inbox. It's made of two
skills that work together through **one shared Teams channel**:

- **Cowork ROI — Team Member skill** (this repository). Every teammate runs it on their own work. It turns
  their Copilot Cowork activity into a clear, de-identified summary — hours saved, the value of that time,
  the kinds of work Copilot helped with, and what they produced — and posts it as easy-to-read tables into
  the shared channel. Names, file names, and prompts are never shared; only totals and categories.
- **Cowork ROI — Team Dashboard skill** (the manager skill). The manager/lead runs it. It reads the shared
  channel, combines everyone's summaries into one anonymized HTML dashboard, and **emails the team a
  newsletter** (the dashboard plus a one-page guide) on a schedule the manager chooses. It only ever reads
  what teammates post — never anyone's files. (Upstream project:
  https://github.com/Fepilot/cowork-roi-team-dashboard.)

To make rollout effortless, this repository also hosts a small web page — the **Installer Studio** — where a
manager pastes their team's Teams channel link once and downloads **both** skills with that channel already
built in. Nobody is ever asked to paste a link. The rest of this guide walks a manager through the whole
process.

## What you'll need first

A **Teams channel** where your team's Cowork reports will be collected — for example
`Cowork report - {your team name}`. If you don't have one yet, create it in Microsoft Teams before you
start, and add the people whose work you want included. Keep the channel just for these reports.

## Set it up — step by step

You only do this **once** for your team.

1. **Open the Installer Studio page** in your web browser:
   https://rance9.github.io/cowork-roi-member/

2. **Copy your team's Teams channel link.** In Microsoft Teams, find the channel in the left-hand list,
   hover over its name, and click the **⋯ More options** button that appears (or right-click the channel).
   Choose **Get link to channel** — older versions of Teams call this **Copy link** — then click **Copy**.

3. **Paste the link** into the box on the page and click **Parse & verify.** The page reads the link and
   shows the **channel name** it found — check it's the right channel.

4. **Download both skills.** Two buttons appear, each already carrying your channel:
   - **Download the manager skill (.zip)** — you install this one.
   - **Download the team-member skill (.zip)** — you send this one to your team.

5. **Install the manager skill (that's you).** Open **Copilot Cowork**, upload the *manager* zip, and ask it
   to install the skill (for example: *“upload this zip file and ask it to install the skill”*). Because your
   channel is already built in, it won't ask you for a link. Once installed, you can say *“build the team
   Cowork ROI dashboard”* any time — or ask it to run on a schedule and email the team automatically.

6. **Share the team-member skill with your team.** Send the *team-member* zip to everyone whose Copilot work
   you'd like included. Each person uploads it in Copilot Cowork and asks it to install the skill — the same
   simple step. Their reports start posting to your channel automatically; no one is asked for a link.

That's the whole setup. From here on, teammates post their summaries and your manager skill rolls them up
into the emailed newsletter — refreshing on its schedule with nothing more for you to do.

> **Want your own Copilot work counted too?** As the manager you can *also* install the team-member skill on
> your own Copilot — that's optional, and only needed if you want your own stats in the team totals.

## What the downloads contain

Each download is an ordinary copy of the matching skill with **your channel already filled in**, so it works
the moment it's installed. (If anyone ever installs a plain, un-configured copy, the skill simply asks for
the channel link the first time it runs, the way it normally would.)

## Is my channel link private?

Yes. The link you paste stays entirely inside your own web browser. It is never sent to a server, and
the page makes no outside network calls — it only builds the download for you, locally.

---

## Prefer to install by hand?

You don't have to let Copilot unpack the zip for you — you can drop the skill into place yourself:

1. **Download** a skill from the page above and **unzip** it. You'll get a single folder — either
   `cowork-roi-member/` (the team-member skill) or `cowork-roi-team-dashboard/` (the manager skill).
2. **Copy that folder** into your Cowork skills directory (use the line that matches the skill you're
   installing):
   ```
   Documents/Cowork/skills/cowork-roi-member/
   Documents/Cowork/skills/cowork-roi-team-dashboard/
   ```
3. Wait about 35 seconds for OneDrive to sync, and the skill is ready to use in Copilot Cowork.

Because your channel is already baked into the folder, there's nothing else to configure.

---

<sub>Maintainer note: `docs/` holds the Installer Studio page (`index.html`, `app.js`, vendored
`jszip.min.js`) and `skill-template/` — browser-fetched mirrors of both skills plus their manifests
(`manifest.json` for the member skill, `manifest-dashboard.json` for the manager skill), regenerated by the
sync workflow. Don't hand-edit `skill-template/`.</sub>

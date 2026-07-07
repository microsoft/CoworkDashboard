# Cowork ROI — Member skill

A self-contained skill for **Microsoft Copilot Cowork** that posts a **de-identified, table-formatted Cowork ROI summary** to your team's Teams channel — with a **privacy opt-out** so you can exclude any chat or task before it posts.

This is the **aggregated / team-rollup member step** companion to the personal [What Cowork Did for Me](https://github.com/Fepilot/What-Cowork-did-for-me) report skill.

## What it does

It harvests your own Copilot Cowork sessions from OneDrive, computes research-anchored **time-saved / value / speed** metrics, and renders them as HTML tables (headline KPIs, time-by-category, value pillars, jobs-to-be-done, work-by-business-process, roles, skills, analyzed → produced, deliverables, activity-by-day).

Privacy by design:
- **Person names, file names and prompts are excluded**
- Business processes are grouped into a short canonical set
- Each deliverable is labelled with the business process it supported (no file names)
- Every session is individually selectable in a privacy opt-out picker before posting

## Download

Grab everything in one file: [`cowork-roi-member.zip`](cowork-roi-member.zip) — contains the full `cowork-roi-member/` skill folder ready to unzip into your Cowork skills directory.

## Install

This skill is **self-contained** — it bundles its own analysis pipeline (`classify.py`, `compute.py`, taxonomy data, harvest references). No other skill is required.

1. Copy the whole [`cowork-roi-member/`](cowork-roi-member/) folder into your Cowork skills directory:
   `Documents/Cowork/skills/cowork-roi-member/`
2. Changes appear after OneDrive sync (~35 seconds).

## Use it

Ask Cowork: **"post my Cowork ROI stats to the team channel."**

See [`cowork-roi-member/README.md`](cowork-roi-member/README.md) and [`cowork-roi-member/SKILL.md`](cowork-roi-member/SKILL.md) for full documentation.

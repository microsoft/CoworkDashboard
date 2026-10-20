# Task-Category Classification — Cowork Team Report (member)

How `scripts/classify.py` assigns each Cowork session to exactly **one** task category. These rules
are shared with the sibling `cowork-roi-report` skill (v48) — keep the two copies in step.

Cowork-fit (High / Moderate / Low) grading is separate and is described in `SKILL.md` §3.

## Part 1 — Task category (deterministic)

Categories follow the **Cowork usage taxonomy** (the product's Description/Examples
definitions). The category describes *the nature of the work*, not just the file
type produced. These are the report's eight labels:

| Category | What it means |
|---|---|
| **Analysis & Research** | Searching org data, synthesizing findings, comparing options, explaining concepts, preparing briefings from multiple sources. |
| **Document & content creation** | Drafting docs/presentations, editing text, creating visuals, organizing files in OneDrive/SharePoint. |
| **Email workflows** | Drafting/replying to emails, summarizing threads, triaging the inbox, managing mail rules — centered on **Outlook**. |
| **Communication workflows** | The same ideas as Email, but centered on **Microsoft Teams**: synthesizing, posting, triaging and managing across Teams **messages and channels** (chats, channel posts, replies, announcements, mentions). |
| **Meeting workflows** | Preparing meeting briefings, recapping transcripts, extracting action items, calendar lookups. |
| **Specialized workflows** | Scheduling calendar events, managing task lists, multi-step M365 workflows, recurring prompts, and connectors (Dynamics 365, ADO Boards, Power BI, Fabric, ServiceNow, Salesforce, SAP). |
| **Write or debug code** | Writing/debugging code, code review, script generation, code analysis. |
| **General assistance / Other** | Product guidance, discovering Copilot capabilities, troubleshooting, learning new skills, casual Q&A. |

**Email vs Communication:** they are deliberately separate. If the synthesis,
posting, triaging or managing happens in **email (Outlook)**, it is **Email
workflows**; if the same kind of work happens in **Teams messages and channels**,
it is **Communication workflows**.

### How a session is assigned — the category rules

**Principle: one category per session, and all of that session's time saved is
attributed to that category alone.** No session is listed or counted under two
categories. Categories describe *where the work happened*, not just the file that
was saved.

The rules are applied **in this order; the first rule that matches decides.**

| # | Rule | Category | Notes |
|---|---|---|---|
| 1 | **Ends in an email, or is inbox triage** — an email is sent, drafted, replied to or forwarded; or the inbox is sorted, flagged, moved or given rules. | **Email workflows** | Applies **even if** the work synthesized Teams chats, channels or meetings along the way. The email is the final output. |
| 2 | **Posts to Teams, or predominantly synthesizes across Teams channels/chats** (Teams reads are at least half of the session's data reads). | **Communication workflows** | Reading one channel as a side input does not qualify. |
| 3 | **Skill work** — creating, attaching, installing, packaging or quality-reviewing a Cowork skill or plugin (goal mentions a skill/plugin, or a skill `.zip` is an input or output). | **Write or debug code** | Always, regardless of the file produced. |
| 4 | **Research — "who did the thinking?"** The goal states research intent (*research, compare, investigate, evaluate, synthesize, analyze, benchmark, assess options*) **and** the session shows real gathering. | **Analysis & Research** | The deck or doc is the *container* for the findings, not the work. See the evidence test below. |
| 5 | **Touches a system outside Microsoft 365** — a CRM or line-of-business app reached via a connector or a third-party MCP server (e.g. Salesforce, Dynamics 365, ServiceNow, Jira, Workday, SAP, GitHub). | **Specialized workflows** *(candidate)* | Becomes the category when nothing else fits (e.g. no saved deliverable). If the session also produced a deliverable, rule 6 decides. |
| 6 | **Tie-break — the final output's format decides.** When more than one category still fits, the format of the final deliverable wins. | By file type (below) | The final deliverable is the **latest-created primary file**; notes, logs, JSON and screenshots are skipped unless nothing else exists. |
| 7 | **Fallback** — no deliverable and several candidates: fixed priority `code → analysis → special → document → comms → meeting → email → general`. No candidates at all → **General assistance**. | — | Rarely reached. |

**File type → category** (used by rule 6):

| Final file | Category |
|---|---|
| `.pptx`, `.docx`, `.pdf`, images, `.xlsx`, `.csv` | Document & content creation *(a built spreadsheet is created content, not analysis)* |
| `.html`, `.py`, `.ps1`, `.js`, `.sql`, `.ipynb`, skill `.zip` | Write or debug code |

#### The research evidence test (rule 4)

Research almost always ends in a deck or a document, so the file type cannot tell
research apart from content creation. The test is **who did the thinking**:

| If the session… | Category |
|---|---|
| **Gathered new information from multiple sources** (web, M365 search, mail, files) and compared, evaluated or drew conclusions — the deck/doc holds the findings | **Analysis & Research** |
| **Took material the user supplied or already had** and mainly structured, designed or polished it | **Document & content creation** |

How the code applies it:

1. **Intent comes from the goal.** Research verbs (above) point to Analysis.
   Content verbs — *draft, design, format, refresh, polish, redesign, build a deck,
   slides, template, convert* — point to Document, unless an explicit research verb
   (*research, investigate, compare, evaluate, synthesize*) is also present.
2. **Evidence comes from the action history, when one exists.** Analysis requires
   **≥ 3 sources**: three or more gathering actions (searches, web fetches, reading
   files, mail, channel messages, transcripts, data queries), **or** three or more
   data input files, **or** `sources_reviewed ≥ 3`. Research intent *without* that
   evidence falls back to the final-output format (usually Document).
3. **No action history** (older sessions known only from their OneDrive folder):
   the goal's intent decides.
4. **Research that ends in an email** stays **Email workflows** (rule 1 runs first).
   **Research that ends in an app or script** is **Write or debug code** — the build
   is the work.

*Why it matters:* Analysis & Research is credited at ~67 min/run (typical) versus
~24 min for Document & content creation. Requiring evidence keeps the higher band for
real research and keeps the report credible.

#### Worked examples

| Session | Category | Rule |
|---|---|---|
| Synthesize Teams channels and meetings into a status email draft | Email workflows | 1 |
| Post my Cowork stats to the team channel | Communication workflows | 2 |
| Review team dashboard skill quality (output `.html`) | Write or debug code | 3 |
| Research consumption-based chargeback models (output `.pptx`) | Analysis & Research | 4 |
| Research a topic, but the log shows no searches or reads (output `.pptx`) | Document & content creation | 4 fails → 6 |
| Propose new case study slide designs (output `.pptx`) | Document & content creation | 6 |
| Pull pipeline from Salesforce and build an account deck | Document & content creation | 5 → 6 |
| Opportunity review in Salesforce, no saved file | Specialized workflows | 5 |
| Analyze CRM pipeline and build a tracker app (output `.html`) | Write or debug code | 6 |

### Counting discipline

- Fold supporting files (notes, READMEs, screenshots, lock files) into the session's
  primary deliverable.
- A category with **no** matching work is reported as **zero** — the report never
  force-fits a session into a high-value bucket.
- Where an activity log recorded runs under several categories, only the runs for the
  session's assigned category are counted; the others are dropped, not reassigned.

### The Document primary-output gate

A session is tagged **Document & content creation** only if it actually
**produced** a genuine content artifact (PowerPoint, Word/PDF, Loop/OneNote,
image, or spreadsheet). An incidental `.md`/`.txt` log or a chat-only session does
not count — this keeps the category honest.

---


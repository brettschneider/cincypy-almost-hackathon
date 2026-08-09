# Background Info

## People

- **Steve Brettschneider** — host/organizer of this effort.

## Organizations

### Pinnacle Solutions Group, Inc.

Steve's employer. A software and data engineering consulting firm headquartered in Cincinnati, Ohio, with additional offices in Charlotte, NC and Nashville, TN.

- **Website:** https://www.pinnsg.com
- **Tagline:** "Your Technology Guides"
- **Contact:** info@pinnsg.com | 513-619-6323

**Core services:**

- **AI Solutions** — implementation services for process automation, model selection, knowledge management, and team training.
- **Data Engineering & Analytics** — building reliable data pipelines and reporting from scattered or manual systems.
- **Custom Development & Integration** — tailored software for specific business workflows, integrated with existing systems.
- **DevOps** — deployment reliability, cloud cost visibility, and scaling practices.
- **Technology Assessments & Strategy** — infrastructure evaluations with prioritized roadmaps aligned to business goals.

**Differentiators:**

- Consultants average 15+ years of field experience.
- Active engagement with emerging tech (regular professional conference attendance).
- Flexible, project-based consultant support model.

**Recognition:**

- Cincinnati Business Courier's Best Places to Work — 7 years.
- Top Workplaces Regional Winner, Gold Badge (2023).
- Charlotte Fast 50 — ranked 17th in 2022 (89.19% growth since 2019).
- Ranked #14 among largest IT consulting firms (2022 local sales).

**Role in this project:** Hosts the CincyPy meetup at the Pinnacle office — natural default venue for the hackathon.

### CincyPy

Cincinnati's Python Meetup / Usergroup.

- **Website:** https://cincypy.com
- **Manager:** Brian Sauer (he does not work for Pinnacle — route organizer/operational questions to him, treat Pinnacle's office as the venue only).

## Project

**The CincyPy "Almost Hackathon"** — a hackathon-like meeting in place of a normal CincyPy meetup, planned for the near future. Output of this project is a planning document for that event.

### Origin

The idea came out of a previous CincyPy meeting and was developed in a Slack conversation between Steve and Brian Sauer on **Sunday, August 2nd, 2026**, continuing into **Monday, August 3rd** (full transcript: [project-genesis.md](project-genesis.md)).

Brian's initial reaction (Monday 1:20 PM) called the idea "nice and text based" and noted that the format gives people time to prep while the inputs are revealed at the meetup.

### Format constraints (from Steve's initial pitch)

- **Meeting length:** ~2 hours total — ~1.5 hours for the challenge, last 30 minutes reserved for optional presentations.
- **No prizes / no contest** — purely creative / show-and-tell. Steve will not participate as a contestant; he'll float around and help anyone who wants it.
- **AI tools are optional** — neither required nor disallowed. Participants may use a frontier API key or run Ollama locally; Steve can host an Ollama instance on the LAN (no-auth REST endpoint) for anyone who'd rather call his than set up their own.
- **Solution language:** Python (Steve's note: "but that does without saying").

### The proposed challenge

Write a **code-review agent** that accepts a single source-code file and returns a "report" with these sections:

1. What was done well in the source code file.
2. What could be improved in the source code file.
3. Identify any bugs or syntax errors in the source code file.
4. *(Extra credit bonus)* A new version of the source code file with bugs fixed and made more efficient or readable.

**Intentionally vague on purpose** to allow creative solutions — web page, CLI tool, etc.; report as `.pdf`, HTML, etc. Input can be any major common language: Python, JS, TS, C#, HTML, etc.

### Pre-made test inputs Steve proposes to provide

- One that's just broken with bad syntax.
- One that runs but is really inefficient and/or bloated.
- One that is pretty good and shouldn't really need any modification.
- One in a nonsensical language that doesn't exist.
- One that's just an English paragraph.

### Pre-event logistics Steve proposes

- Announce the hackathon with **setup details (but NOT the problem)** so people can get their laptops ready ahead of time.
- Include Ollama install/setup instructions in the pre-announcement.

### Roles agreed in the genesis conversation

- **Steve** — owns the "suggested technologies" list (committed to writing it up "in the next day or so" on Monday Aug 3 at 10:27 PM).
- **Brian** — owns installing/configuring the suggested technologies and writing the basic setup docs (offered Monday Aug 3 at 1:35 PM). Brian also runs CincyPy operations (announcement, RSVP, etc.).
- Steve floated asking an LLM to draft the setup docs as an alternative; Brian left that as an open option ("Or I guess an LLM could do that 🙂").

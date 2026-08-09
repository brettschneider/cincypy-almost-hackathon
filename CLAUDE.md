# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Planning repository for the **CincyPy "Almost Hackathon"** — a one-off hackathon-style meeting replacing a regular CincyPy meetup. The deliverable of this project is a **planning document** for the event, not source code.

There is no application code, build system, or test suite — only markdown. Files:

- [background-info.md](background-info.md) — people, organizations, project context, format constraints, the proposed challenge, and the Steve/Brian role split.
- [project-genesis.md](project-genesis.md) — Slack transcript (Aug 2–3, 2026) where Steve pitched the idea and Brian responded.
- [project-genesis.png](project-genesis.png) — screenshot of the same Slack conversation.
- [pre-meeting.md](pre-meeting.md) — setup guide sent to attendees in advance. Contains logistics, schedule, LLM path options (frontier API / local Ollama / Steve's LAN endpoint), and pre-meeting setup checks. **Does not contain the challenge prompt.**
- [announcement.md](announcement.md) — public-facing announcement in two flavor variants (longer Meetup.com, shorter LinkedIn). **Does not contain the challenge prompt** beyond the general "AI agent in Python" framing.

Future work here will likely be additional planning artifacts:
- **Still pending:** the problem-statement file itself (the actual four-section code-review prompt — kept locked until the meeting), the pre-made test input files (Steve's five planned samples), and Steve's standalone "suggested technologies" list (committed in the genesis chat on Aug 3).
- **Possibly pending:** a Brian-owned setup doc. The setup material in [pre-meeting.md](pre-meeting.md) currently covers most of what was envisioned; if Brian produces a separate, complementary doc, it can sit alongside it.

The code-review agents are **not** built here — those are written by hackathon attendees.

## The event

- **Duration:** ~2 hours total — ~1.5 hours for the challenge, last 30 minutes reserved for optional presentations.
- **Tone:** Creative show-and-tell. **No prizes, no contest.** Steve will float and help but will not participate as a contestant.
- **Solution language:** Python (per Steve: "but that does without saying").
- **AI tools:** Optional — neither required nor disallowed. Attendees may use a frontier API key or run Ollama locally. Steve can host a no-auth Ollama instance on the LAN as a REST endpoint for anyone who'd rather call his than set up their own.

## The challenge (intentionally vague)

Build a code-review agent that takes a single source-code file and returns a report with these sections:

1. What was done well.
2. What could be improved.
3. Bugs or syntax errors.
4. *(Extra credit)* A rewritten version of the file with bugs fixed and made more efficient or readable.

Intentionally open-ended on output format (web page, CLI tool, etc.) and report format (`.pdf`, HTML, etc.). Input may be in any common language: Python, JS, TS, C#, HTML, etc.

## Pre-made test inputs Steve plans to provide

- One with bad syntax.
- One that runs but is inefficient/bloated.
- One that is pretty good and needs little modification.
- One in a nonexistent/nonsensical language.
- One that is just an English paragraph.

## Roles and routing

- **Steve Brettschneider** — host/organizer; Pinnacle Solutions Group employee ([pinnsg.com](https://www.pinnsg.com)). Owns the suggested-technologies list. Drafted the in-repo setup guide ([pre-meeting.md](pre-meeting.md)) and the public announcement ([announcement.md](announcement.md)).
- **Brian Sauer** — CincyPy manager; he does **not** work for Pinnacle — route CincyPy organizer/operational questions to him (announcement, RSVP, venue). Per his offer in the genesis chat, Brian was originally on the hook for installing/configuring the suggested technologies and writing basic setup docs; most of the setup content has since landed in [pre-meeting.md](pre-meeting.md). If Brian produces a complementary doc, route it through him.
- **Pinnacle Solutions Group** — hosts CincyPy at their office; the natural default venue for the hackathon.

## Conventions for adding to this repo

- Keep planning artifacts in markdown alongside the existing files.
- Do not introduce code, build tooling, or CI configuration — this repo is documentation-only until the hackathon produces code artifacts, and even then those belong to the attendees, not here.
- **Preserve the challenge-vs-setup split.** The challenge prompt is revealed at the event and must not appear in pre-announcement material. Setup details (Ollama install, suggested tech, LAN endpoint) are fair game for the pre-announcement.
- When updating [project-genesis.md](project-genesis.md), treat it as a transcript — preserve wording, timestamps, and ordering. Add new messages under the appropriate day header rather than rewriting earlier turns.

# CincyPy "Almost Hackathon" — Planning Repo

> **Private planning repository.** This is the working folder for Steve Brettschneider and Brian Sauer as they plan the CincyPy "Almost Hackathon" — a one-off hackathon-style meeting replacing a regular CincyPy meetup. There is no application code here, only markdown planning artifacts. The deliverables are documents, not software.

---

## Primary deliverables

These two files are what this repo exists to produce. Everything else is supporting context.

- **[announcement.md](announcement.md)** — the public-facing announcement, with two flavor variants: a longer Meetup.com post and a shorter LinkedIn post. **Does not reveal the challenge prompt** beyond the general "AI agent in Python" framing — the specifics are kept back for the meeting itself.
- **[pre-meeting.md](pre-meeting.md)** — the setup guide sent to attendees in advance. Covers logistics, schedule, LLM path options (frontier API / local Ollama / Steve's LAN endpoint), pre-meeting setup checks, and what to bring. **Does not reveal the challenge prompt** — same reason.

Both files are intentionally vague about the actual project so attendees aren't primed before the reveal. The full challenge prompt is held back until the start of the meeting.

---

## Supporting context

These files exist to give collaborators (and a future Claude instance) the background they need to make changes without re-deriving everything from scratch.

- **[background-info.md](background-info.md)** — people, organizations, project context, format constraints, the proposed challenge, and the Steve/Brian role split. Start here if you're new to the repo.
- **[CLAUDE.md](CLAUDE.md)** — guidance for Claude Code (and any future AI assistant) operating in this repo. Captures the invariants: the challenge-vs-setup split, who owns what, what *not* to add (no code, no CI, no tooling).
- **[project-genesis.md](project-genesis.md)** — the original Slack transcript (Aug 2–3, 2026) where Steve pitched the idea and Brian responded. Treated as a transcript — preserve wording, timestamps, and ordering when adding to it.
- **[project-genesis.png](project-genesis.png)** — screenshot of the same Slack conversation.

---

## What's still pending

Artifacts that haven't been written yet but are likely to land here before the event:

- **The problem-statement file itself** — the actual code-review challenge prompt with the four report sections. Held back from this repo until needed; may live here the night of, or only on the projector.
- **Pre-made test input files** — Steve's five planned samples (bad syntax, inefficient-but-runs, pretty-good, nonsensical language, English paragraph). These go to attendees at the start of the meeting, so they may not need to be in this repo.
- **Steve's standalone "suggested technologies" list** — committed to in the genesis chat on Aug 3. Currently lives inside [pre-meeting.md](pre-meeting.md) as a brief mention; a separate doc is possible if it grows.

---

## Conventions at a glance

- Markdown only. No code, no build tools, no CI.
- Preserve [project-genesis.md](project-genesis.md) as a transcript — add new messages under the appropriate day header, don't rewrite earlier turns.
- See [CLAUDE.md](CLAUDE.md) for the full set of repo conventions.

# CincyPy "Almost Hackathon" — Pre-Meeting Setup Guide

> **Read this before the meeting.** It covers logistics, the schedule, and how to get your laptop ready so we can spend our 2 hours building instead of installing. **The challenge prompt itself is intentionally NOT included here** — you'll see it for the first time at the meeting.
>
> **One thing we will tell you in advance:** the project is to build an **AI agent application** in Python. That's all we'll say until the night of — the specifics of what the agent does, what its inputs and outputs look like, and what "done" looks like — all revealed live. The point of saying this much is so you can think about the shape of the problem (and the tools you might want) before you show up.

### Why "Almost Hackathon"?

Because there isn't a competition to it. No prizes, no winners or losers. Just folks — solo or in small groups — working in the same room on the same project for an evening. Everything else below follows from that: there's nothing to lose, and showing your work is a choice, not a requirement.

---

## At a glance

- **Date:** [DATE]
- **Time:** 6:30 PM – 8:30 PM (doors open at 6:00 PM)
- **Venue:** Pinnacle Solutions Group office, [FULL ADDRESS, SUITE/ROOM]
- **Parking:** [DETAIL — lot, street, garage]
- **Food:** [DETAIL — what's provided, what's BYO]
- **Contact day-of:** Steve [phone] · Brian [phone]

---

## The format

| Clock | What |
|---|---|
| 6:30 PM – 6:40 PM | Welcome. Challenge prompt revealed. Sample inputs handed out. |
| 6:40 PM – 8:00 PM | Build time. Coaches float around to help. |
| 8:00 PM – 8:30 PM | Optional show-and-tell. Anyone who wants to demo their solution gets ~1–2 minutes. |

(Times are approximate. Build window is ~80 minutes; show-and-tell window is ~30 minutes; the welcome is intentionally short.)

**No prizes, no judges.** This is creative tinkering. Showing your work is welcome but not required.

**Languages:** Solutions in Python. (Inputs to your solution can be any common language — that's part of the design.)

**Teams:** Solo or pairs. No formal team-up process — just find someone at the meeting if you want a partner.

---

## What to bring

- A laptop with **Python 3.10+** installed and working.
- Your editor of choice.
- A way to call an LLM. Pick **one** of the three options below.
- *(Optional)* Snacks/drinks if the provided food isn't enough for you.

### A note on the LLM options

**None of the three options below are required.** You can use any of them, all of them, or none of them. The chain is:

- You **can** use a frontier model (OpenAI, Anthropic, Google, etc.) — totally optional.
- If you'd rather not pay for / set up a frontier API, you **can** install Ollama on your own laptop and run a model locally — also totally optional.
- If you don't want to do either of the above, **Steve will have a no-auth Ollama instance running on the office LAN** that you can point your code at. Just one more option, still optional.

Pick whichever path (if any) you like. Coaches will be around to help you get any of them working during the meeting if you hit a snag.

---

## Option 1 — Use a frontier API key (easiest if you already have one)

If you already have an API key for OpenAI, Anthropic, Google, etc., bring it and use the SDK of your choice. No setup at the meeting required beyond installing the SDK.

Quick sanity check before the meeting:

```bash
python -c "import sys; assert sys.version_info >= (3, 10); print('ok')"
pip install openai   # or anthropic, google-genai, etc.
```

(Whatever SDK you plan to use — make sure `pip install` succeeds for it before the meeting.)

## Option 2 — Run Ollama locally

Recommended if you want to keep everything on your laptop with no API keys.

### Install Ollama

The current install instructions live on Ollama's site — start at <https://ollama.com/download> and pick your OS. A snapshot of what's there as of this writing:

- **macOS** (Sonoma 14 or later): download <https://ollama.com/download/Ollama.dmg>, open the `.dmg`, and drag Ollama to Applications. The desktop app comes with the CLI included.
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`
- **Windows** (10 or later): either run this PowerShell one-liner:
  ```powershell
  irm https://ollama.com/install.ps1 | iex
  ```
  …or download <https://ollama.com/download/OllamaSetup.exe> and run the installer.

If anything looks stale by the time you read this, follow the instructions on <https://ollama.com/download> — they stay more current than this doc.

Verify it works:

```bash
ollama --version
```

### Pull a model in advance

Ollama's model library is large — browse <https://ollama.com/library> to see what's available, and pick whatever looks interesting to you. **Don't worry about picking "the right one" before the meeting** — you can swap models freely during the night, and Steve can suggest options when you arrive if you'd like a pointer.

A few things to know as you choose:

- Models range from ~1 GB to tens of GB. Smaller downloads faster; larger ones tend to give better answers. Pick something that fits your laptop and your patience for a one-time download.
- **Do the pull at home on your own Wi-Fi.** Don't try to pull a multi-GB model on the office Wi-Fi the night of.

```bash
ollama pull <model-name>     # e.g. ollama pull llama3.1:8b
ollama serve                 # starts the local server on http://localhost:11434
```

### Sanity check

Once `ollama serve` is running, open the **Ollama desktop app** (the UI that came with the install). It usually has a chat box — type something like *"Say hello in one word."* into it. If you get a sensible reply back, your local Ollama is working end-to-end. That's all you need for the meeting.

You don't need to use `curl`, the REST API, or any SDKs before the night of — that all comes later, in your own code.

### Python SDK

```bash
pip install ollama
```

The official `ollama` Python package talks to the local server over HTTP. Docs: <https://github.com/ollama/ollama-python>.

## Option 3 — Use Steve's no-auth Ollama endpoint on the LAN

If you don't want to install Ollama on your machine, Steve will have an Ollama instance running on the office network during the meeting. It's a plain REST endpoint with **no authentication** — that's fine because it's only reachable on the local Wi-Fi.

- **Base URL:** `http://[HOSTNAME-OR-IP]:11434` (final URL will be posted at the meeting and on the projector)
- **Available models:** `[LIST]` (will be confirmed before the meeting)
- **API:** Standard Ollama REST API — same shape as a local install. The Python `ollama` SDK will work if you point it at the remote host:

```python
import ollama
client = ollama.Client(host='http://[HOST]:11434')
resp = client.generate(model='[MODEL]', prompt='Hello')
```

**Caveats:**

- It's a shared instance. Don't hammer it with 50 concurrent requests during the build session — be a good neighbor.
- If the office Wi-Fi is flaky, your call may fail. Have a local fallback in mind.
- Don't put anything sensitive in your prompts — it's a no-auth endpoint by design.

---

## What we're *not* prescribing

We're deliberately not suggesting libraries or frameworks for the build. The whole point of the evening is to see what people come up with given a wide-open canvas — handing everyone the same stack would defeat that. Pick whatever Python tools you're comfortable with, or try something new. Coaches can help you sort out library choices on the night if you'd like a second opinion.

The only real constraint is **Python 3.10+** and **whichever LLM path (if any) you chose above**. Everything else is yours to decide.

---

## A few things you can do at home to hit the ground running

None of these are required. They're just ways to make the meeting smoother.

1. **Verify your LLM path works end-to-end.** Write a 5-line script that sends a prompt and prints the response, using whichever option (1, 2, or 3) you chose. Run it. Fix any install issues now, not at the meeting.
2. **Decide your output format ahead of time.** CLI tool? HTML page? PDF? Knowing this before you see the prompt saves decision fatigue during the build window.
3. **Skim the Ollama Python SDK README** if you're going the Ollama route — the API is small.
4. **Charge your laptop.** A 90-minute build session plus demos is a lot of battery.

---

### AI-assisted dev tools (Claude Code, Copilot, Cursor, etc.)

You're also welcome — but not required — to use an AI-assisted dev tool to help you write the code: **Claude Code, GitHub Copilot, Cursor, Devin, Windsurf, Cody, whatever you like.** Just like the LLM-call decision above, this is a "you do you" choice. Some folks will use them heavily. Some won't touch them. Both are fine.

**Installing and authenticating your dev tools is your responsibility before the meeting.** We won't have time to debug IDE installs during the session. A quick way to tell if yours is ready: open your editor and ask it to write a hello-world function. If it works, you're set.

### Your editor / IDE

You're on your own here — use whatever you normally use. **VS Code, PyCharm, Vim, Emacs, JupyterLab, IDLE** — whatever's on your laptop. There's no prescribed tool. If you don't currently have a Python editor installed, install one before the meeting so you're not setting it up in front of everyone.

## Coaches at the meeting

You're not on your own. **[N] coaches will be floating around** during the build session — Steve plus [others]. If you're stuck on getting Ollama working, picking an output format, debugging your prompts, or anything else, just raise a hand. That's literally why we're there.

This applies whether you're a beginner who's never called an LLM from Python before, or someone who's done it a hundred times and just wants a second pair of eyes on an edge case.

## Who this is for

**Everyone.** Experts, intermediates, and people who are still figuring out what a `for` loop does — all welcome. We're explicitly looking for creativity, not credentials. If you've never written Python before but want to give it a shot, the coaches can pair with you. If you've been writing Python for fifteen years, you'll probably find the interesting part in the format, not the code.

## Day-of checklist

- [ ] Laptop charged
- [ ] Python 3.10+ working
- [ ] Chosen LLM path verified end-to-end (one successful test call)
- [ ] Editor of choice ready
- [ ] Any throwaway code samples you want to test with (optional)

---

## What you'll get at the meeting

- The actual challenge prompt (revealed live).
- A handful of pre-made sample input files from Steve — designed to cover interesting cases.
- Wi-Fi access (info posted in the office).
- Steve's LAN Ollama endpoint details (if you're going that route).
- Pizza / snacks / coffee — provided by Pinnacle (as host).

---

## Questions?

- **Logistics (RSVP, Meetup.com, the announcement post):** Brian Sauer — CincyPy organizer.
- **Venue, food, format, suggested tech, setup help:** Steve Brettschneider — host (Pinnacle Solutions Group).
- **"Can I use language X?" / "Can I use framework Y?"** Yes. The only hard rule is "solution is Python." Everything else is fair game.

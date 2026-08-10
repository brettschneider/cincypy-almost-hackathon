# CincyPy "Almost Hackathon" — The Challenge

> **Revealed at the meeting.** This is the actual problem statement for the night. Pre-meeting docs ([pre-meeting.md](pre-meeting.md), [announcement.md](announcement.md)) deliberately did not include it — so if anything here surprises you, that's on purpose.

---

## Your task

Build an **AI code-review agent** in Python.

The agent accepts **a single source-code file** as input and produces **a "report"** as output. The report must include these four sections:

1. **What was done well** in the source code file.
2. **What could be improved** in the source code file.
3. **Bugs or syntax errors** identified in the source code file.
4. *(Extra credit)* **A rewritten version of the source code file** with bugs fixed and made more efficient or readable.

That's the whole spec. The rest is up to you.

---

## What "report" means is your call

The prompt deliberately does not say what format the report should be. Some directions you might go:

- A CLI tool that prints the report to the terminal.
- An HTML page (local file, or rendered by a tiny web app you spin up).
- A PDF.
- A markdown file.
- Something else entirely.

How you **structure** the report is also your call. As long as a reader can find those four sections (and you made a good-faith attempt at section 4 for the extra credit), you pass.

## What languages can the input file be in?

Any common language: Python, JavaScript, TypeScript, C#, HTML/CSS, Java, Go, Rust, etc. Your agent doesn't need to handle every one of them — it just needs to handle whatever you test it with.

If you want to impress, handle the edge cases in the sample inputs (see below). If you don't, that's fine — call out what you skipped.

---

## The sample inputs

Steve has prepared five sample files for you to throw at your agent. Each one is designed to exercise a different edge case:

| # | Sample | What it tests |
|---|---|---|
| 1 | One that's just broken with bad syntax. | Can your agent recognize a file it can't even parse? Does it say so gracefully, or hallucinate a review? |
| 2 | One that runs but is really inefficient / bloated. | Can your agent spot O(n²) where O(n) would do? Dead code? Redundant work? |
| 3 | One that's pretty good and shouldn't need much modification. | Can your agent resist inventing problems that aren't there? (The hardest sample.) |
| 4 | One in a nonsensical language that doesn't exist. | What does your agent do when the input isn't code at all? Does it recognize that? |
| 5 | One that's just an English paragraph. | Same question, from the other direction — non-code in, non-code out, or a polite "this isn't source code"? |

You don't have to handle all five perfectly. Pick the ones that interest you. The variety is there so you can pick your own adventure.

---

## Ground rules

- **Solutions must be in Python.** That's the only hard rule.
- **AI tools are optional.** Use a frontier API key, run Ollama locally, or call Steve's no-auth LAN endpoint — or don't use any of them. Your call.
- **AI-assisted dev tools are also optional.** Claude Code, Copilot, Cursor, Devin, whatever you like — or none. Your call.
- **Solo or pairs.** No formal team-up. Just find someone if you want to pair.
- **No prizes, no judges.** Show-and-tell is welcome at the end if you'd like to demo, but it's not required.

---

## Timing

- **6:30 – 6:40 PM** — You're reading this now. Get oriented, claim a seat, decide solo or pair.
- **6:40 – 8:00 PM** — Build. Coaches float around to help. ~80 minutes.
- **8:00 – 8:30 PM** — Optional show-and-tell. ~1–2 minutes each if you want to demo.

---

## What to think about during the build

You don't have to answer all of these — they're just prompts if you get stuck deciding what to make:

- **Output format.** HTML, CLI, PDF, something else? You probably want to commit to this in the first 10 minutes — it shapes everything else.
- **Section 4 (the rewrite).** How do you generate a new file from the original? Do you ask the model for the full file in one shot? Do you stream it? Do you diff it against the original and show what changed?
- **The "this isn't code" cases.** Samples 4 and 5 are interesting because they're easy to get wrong. How does your agent behave when it can't actually review code?
- **Prompt design.** How do you structure the prompt to the model? System prompt vs. user prompt? One big call vs. one call per section? There are real tradeoffs here.
- **Robustness.** What happens on a model timeout? A malformed input? A 500-line file? A 5-line file? You don't have to handle all of it — but a little thought here goes a long way.

---

## When the clock hits 8:00 PM

Stop where you are. Don't keep polishing — the show-and-tell is more interesting when people see where you actually landed, not a slightly-more-polished version of the same thing.

If you want to demo, you'll get about 1–2 minutes. A few sentences on what you made, a quick walkthrough of one of the sample inputs, done. If you'd rather not, that's fine — hang out, watch other demos, ask questions.

---

## One last thing

The whole point of the evening is to see what folks come up with given a wide-open canvas. There's no "correct" version of this. If your agent prints to stdout, great. If it's a slick little web page, great. If it produces a beautifully typeset PDF, great. If it's a 40-line script that just calls an LLM and dumps the result, also great — that's a perfectly valid solution and a fine starting point for future tinkering.

Have fun.

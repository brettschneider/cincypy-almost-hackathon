#!/usr/bin/env python3
"""CincyPy "Almost Hackathon" reference solution — stdlib-only.

Talks to a local Ollama instance over its native REST API (no third-party
packages) and asks a model to review a single source file. Output goes to
stdout as plain text by default; with -o OUTPUT.md, writes the report as
markdown.

    python code_review.py SOURCE_FILE [-m MODEL] [-p PROMPT.md] [-o REPORT.md]
                                   [--with-rewrite] [--host URL]

Defaults: model = qwen3.5:4b, host = http://localhost:11434, prompt = built-in,
output = stdout (plain text), rewrite = off.

The destination determines what the model is asked to produce: when writing
to stdout the script asks for plain text (no markdown to strip afterwards),
and when writing to a file it asks for the markdown a reader would expect.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# --- defaults ---------------------------------------------------------------

DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_HOST = "http://localhost:11434"

# Plain-text review prompt (used when output is stdout).
REVIEW_PROMPT_TEXT = """\
You are a careful, no-nonsense code reviewer. The user will paste a single
source-code file. Output plain text — NO markdown, no `#` headings, no
`**bold**`, no backticks for emphasis. Use these section headings (one per
line, in this order, in ALL CAPS):

WHAT WAS DONE WELL

WHAT COULD BE IMPROVED

BUGS OR SYNTAX ERRORS

Under each section, use bullet lines starting with "- ". Be specific and
grounded — quote identifiers or short constructs when useful. Do not invent
issues that aren't there. If there are no bugs, say "No bugs found." under
the bugs section rather than padding it. Put a single blank line between
sections and between bullets.

If the input is not source code at all (an English paragraph, a nonsensical
made-up language, prose with no code, etc.), say so plainly under each
section — e.g. "This does not look like source code." — instead of
hallucinating a review. Do not output any section headings that are not
listed above.
"""

# Markdown review prompt (used when output is a file via -o).
REVIEW_PROMPT_MD = """\
You are a careful, no-nonsense code reviewer. The user will paste a single
source-code file. Produce a markdown report with EXACTLY these three
sections, in this order, using these exact headings:

## What was done well
## What could be improved
## Bugs or syntax errors

Under each section, use bullet points. Be specific and grounded — quote
identifiers, line-level constructs, or short snippets when useful. Do not
invent issues that aren't there. If there are no bugs, say "No bugs found."
under the bugs section rather than padding it.

If the input is not source code at all (an English paragraph, a nonsensical
made-up language, prose with no code, etc.), say so plainly under each
section — e.g. "This does not look like source code." — instead of
hallucinating a review. Do not output any section headings that are not
listed above.
"""

# Rewrite prompt — same shape for both destinations: a single fenced code
# block. Fences are the shape qwen3.5:4b writes well, and they're trivially
# renderable as indented plain text for stdout without lossy parsing.
REWRITE_PROMPT = """\
You are rewriting a single source-code file to fix the bugs you would call
out in a review AND to make it more efficient or readable.

Respond with ONLY the rewritten file wrapped in a single fenced code block.
Use a fenced block with the appropriate language tag (```python,
```javascript, etc.) — or ```text if the language is unclear. No prose
before or after the fence.

IMPORTANT: Preserve the original function signatures, parameter names,
and parameter counts. You are improving the body and fixing bugs — not
changing interfaces. If the input is not source code, respond with
exactly:

```text
This input is not source code, so there is nothing to rewrite.
```
"""


# --- Ollama REST plumbing ---------------------------------------------------

DEFAULT_TIMEOUT = 300  # seconds; overridable via --timeout


class CodeReviewError(RuntimeError):
    """Raised when the script can't do its job — caught in main() and printed
    once with a clean exit code, instead of leaking stack traces or repeating
    the print/exit dance at every call site."""


@dataclass
class OllamaResult:
    text: str


def call_ollama(
    host: str,
    model: str,
    system: str,
    user: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> OllamaResult:
    """POST /api/chat, non-streaming. Returns the assistant's text."""
    url = host.rstrip("/") + "/api/chat"
    body = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 404 typically means the model name isn't pulled. Hint at it.
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        hint = (
            " — is the model pulled? Try `ollama pull <model>`."
            if e.code == 404
            else ""
        )
        raise CodeReviewError(
            f"Ollama HTTP {e.code} {e.reason}{hint}\n{detail}".strip()
        ) from e
    except urllib.error.URLError as e:
        raise CodeReviewError(
            f"Could not reach Ollama at {host}. Is `ollama serve` running?\n"
            f"  ({e.reason})"
        ) from e

    msg = payload.get("message") or {}
    text = msg.get("content", "")
    if not text:
        raise CodeReviewError(
            f"Ollama returned an empty response. Full payload: {payload!r}"
        )
    return OllamaResult(text=text)


# --- review stages ----------------------------------------------------------

def review_sections_1_3(
    host: str, model: str, prompt: str, source: str, timeout: int,
) -> str:
    """First call: sections 1-3."""
    print(f"[code_review] reviewing with {model}...", file=sys.stderr)
    user_msg = (
        "Please review this source file:\n\n"
        "```\n" + source + "\n```\n"
    )
    result = call_ollama(host, model, prompt, user_msg, timeout)
    return result.text.strip()


# --- prompt + report assembly ----------------------------------------------

def load_prompt(path: Path | None, default: str) -> str:
    """Read prompt text from a markdown file, or fall back to default."""
    if path is None:
        return default
    return path.read_text(encoding="utf-8")


def extract_rewrite_block(model_response: str) -> tuple[str, str]:
    """Pull the (body, lang) of the first fenced code block out of a model
    response. Defaults lang to "text" if missing. Returns ("", "") if no
    fence is found — caller decides whether that's an error."""
    lines = model_response.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            start = i
            break
    if start is None:
        return "", ""

    lang = lines[start].strip().lstrip("`").strip() or "text"
    end = None
    for j in range(start + 1, len(lines)):
        if lines[j].lstrip().startswith("```"):
            end = j
            break
    if end is None:
        end = len(lines)
    body = "\n".join(lines[start + 1 : end])
    return body, lang


def build_report_text(sections_1_3: str, rewrite: tuple[str, str] | None) -> str:
    """Assemble the plain-text report (stdout)."""
    parts = [sections_1_3.rstrip()]
    if rewrite is not None:
        body, lang = rewrite
        parts.append("")
        parts.append(f"REWRITTEN VERSION [{lang}]")
        parts.append("")
        # Indent the rewritten body 4 spaces so it visually reads as a
        # code block in a terminal.
        for line in body.splitlines():
            parts.append(f"    {line}" if line else "")
    return "\n".join(parts).rstrip() + "\n"


def build_report_md(sections_1_3: str, rewrite: tuple[str, str] | None) -> str:
    """Assemble the markdown report (-o)."""
    parts = [sections_1_3.rstrip()]
    if rewrite is not None:
        body, lang = rewrite
        parts.append("")
        parts.append("## Rewritten version")
        parts.append("")
        parts.append(f"```{lang}")
        parts.append(body.rstrip())
        parts.append("```")
    return "\n".join(parts).rstrip() + "\n"


# --- CLI --------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Review a source file with a local Ollama model.",
    )
    p.add_argument(
        "source",
        type=Path,
        help="Path to the source-code file to review.",
    )
    p.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "-p", "--prompt",
        type=Path,
        default=None,
        help=(
            "Path to a markdown file whose contents replace the built-in "
            "system prompt (sections 1-3)."
        ),
    )
    p.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write the report to this markdown file instead of stdout.",
    )
    p.add_argument(
        "--rewrite-prompt",
        type=Path,
        default=None,
        dest="rewrite_prompt",
        help=(
            "Optional path to a markdown file overriding the built-in rewrite "
            "prompt (section 4). Implies --with-rewrite."
        ),
    )
    p.add_argument(
        "--with-rewrite",
        action="store_true",
        help="Also ask the model to produce a rewritten version (section 4).",
    )
    p.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Ollama base URL (default: {DEFAULT_HOST}).",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=(
            "Per-call HTTP timeout in seconds "
            f"(default: {DEFAULT_TIMEOUT})."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except CodeReviewError as e:
        print(f"code_review: {e}", file=sys.stderr)
        return 1


def _run(argv: list[str] | None) -> int:
    args = _build_parser().parse_args(argv)

    source: Path = args.source
    if not source.is_file():
        raise CodeReviewError(f"not a readable file: {source}")
    try:
        source_text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try lossy so very long binary-ish files don't trip us.
        source_text = source.read_text(encoding="utf-8", errors="replace")

    # Pick prompts based on destination: plain text for stdout, markdown
    # for a file. The model produces exactly what the destination expects,
    # so there's nothing to convert downstream. The rewrite prompt stays
    # the same — it always asks for a fenced code block, which both
    # destinations can render (markdown keeps it; stdout indents it 4sp).
    if args.output is None:
        review_prompt_default = REVIEW_PROMPT_TEXT
        build_report = build_report_text
    else:
        review_prompt_default = REVIEW_PROMPT_MD
        build_report = build_report_md

    review_prompt = load_prompt(args.prompt, review_prompt_default)
    rewrite_prompt = load_prompt(args.rewrite_prompt, REWRITE_PROMPT)

    sections = review_sections_1_3(
        args.host, args.model, review_prompt, source_text, args.timeout,
    )

    rewrite_block: tuple[str, str] | None = None
    if args.with_rewrite or args.rewrite_prompt is not None:
        print(f"[code_review] asking {args.model} for a rewrite...", file=sys.stderr)
        user_msg = (
            "Here is the file to rewrite. Fix bugs, improve efficiency and "
            "readability, and return the full rewritten version.\n\n"
            "```\n" + source_text + "\n```\n"
        )
        result = call_ollama(args.host, args.model, rewrite_prompt, user_msg, args.timeout)
        rewrite_block = extract_rewrite_block(result.text.strip())

    report = build_report(sections, rewrite_block)

    if args.output is None:
        sys.stdout.write(report)
        sys.stdout.flush()
    else:
        args.output.write_text(report, encoding="utf-8")
        print(f"[code_review] wrote {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

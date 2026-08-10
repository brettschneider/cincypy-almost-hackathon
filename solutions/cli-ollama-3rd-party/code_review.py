#!/usr/bin/env python3
"""CincyPy "Almost Hackathon" reference solution — third-party + rich.

Same shape as [./code_review.py](./code_review.py), but adds [rich](https://rich.readthedocs.io/)
for terminal-side polish and a unified diff between the original source and the
model's rewrite.

    python code_review.py SOURCE_FILE [-m MODEL] [-p PROMPT.md] [-o REPORT.md]
                                   [--with-rewrite] [--host URL]

Output routing:

- With `-o FILE.md`: writes raw markdown (review + fenced rewrite + fenced
  unified diff). The same shape a reader expects when they open the file.
- Without `-o`, on a TTY: prints the review as rendered Markdown, the rewrite
  as a syntax-highlighted code panel, and a unified diff between the original
  source and the rewrite — all colored and wrapped to the terminal width.
- Without `-o`, piped (`| cat`, `| less`): rich auto-disables ANSI and prints
  the same content as plain text. The prompt sent to the model is the markdown
  variant in both stdout cases (a reader wants the same headings either way).

Defaults: model = qwen3.5:4b, host = http://localhost:11434, prompt = built-in,
output = stdout (rich terminal rendering), rewrite = off.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import click
import ollama
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status
from rich.syntax import Syntax

# --- defaults ---------------------------------------------------------------

DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_HOST = "http://localhost:11434"

# Markdown review prompt — used for stdout AND for -o. The plain-text prompt
# from the no-rich version isn't needed here: rich renders markdown for the
# TTY case, and the piped case just gets the markdown source as text. The
# canonical -o file is also markdown, so one prompt serves all three cases.
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
# renderable as syntax-highlighted code by rich.
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


# --- errors -----------------------------------------------------------------


class CodeReviewError(RuntimeError):
    """Raised when the script can't do its job — caught in main() and printed
    once with a clean exit code, instead of leaking stack traces or repeating
    the print/exit dance at every call site."""


# --- review stages ----------------------------------------------------------

DEFAULT_TIMEOUT = 300  # seconds; overridable via --timeout


def _call(
    client: ollama.Client,
    model: str,
    system: str,
    user: str,
) -> str:
    """Single /api/chat call, non-streaming. Returns the assistant's text.

    Maps HTTP-layer failures to CodeReviewError so main() can present a
    single, friendly message."""
    try:
        resp = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=False,
            options={"temperature": 0.2},
        )
    except ollama.ResponseError as e:
        # 404 typically means the model name isn't pulled. Hint at it.
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        hint = (
            " — is the model pulled? Try `ollama pull <model>`."
            if status == 404
            else ""
        )
        raise CodeReviewError(f"Ollama error: {e}{hint}") from e
    except ollama.RequestError as e:
        raise CodeReviewError(
            f"Could not reach Ollama at {client._base_url}. "
            f"Is `ollama serve` running? ({e})"
        ) from e

    msg = resp.get("message") or {}
    text = msg.get("content", "")
    if not text:
        raise CodeReviewError(
            f"Ollama returned an empty response. Full payload: {resp!r}"
        )
    return text.strip()


def review_sections_1_3(
    client: ollama.Client,
    model: str,
    prompt: str,
    source: str,
    spinner: Console,
) -> str:
    """First call: sections 1-3."""
    user_msg = (
        "Please review this source file:\n\n"
        "```\n" + source + "\n```\n"
    )
    with spinner.status(f"[bold cyan]reviewing with {model}...[/bold cyan]"):
        return _call(client, model, prompt, user_msg)


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


def unified_diff_text(
    original: str, rewritten: str, source_label: str,
) -> str:
    """Build a unified diff string between the original and rewritten source.

    Uses stdlib difflib — the only diff machinery we need; rich just renders
    the output as a syntax-highlighted diff block (Pygments ships a Diff
    lexer, so coloring falls out for free)."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        rewritten.splitlines(keepends=True),
        fromfile=source_label,
        tofile=f"{source_label} (rewritten)",
        # lineterm="" so trailing-newline handling doesn't double up when we
        # join lines back together below.
        lineterm="",
    )
    return "".join(diff)


def build_report_md(
    sections_1_3: str,
    rewrite: tuple[str, str] | None,
    diff_text: str,
    source_label: str,
) -> str:
    """Assemble the markdown report written to -o FILE.

    Always includes:
    - sections 1-3 as plain markdown
    - the rewrite section (heading + fenced code block) when --with-rewrite
    - the diff section (heading + fenced diff block) when --with-rewrite
    """
    parts = [sections_1_3.rstrip()]
    if rewrite is not None:
        body, lang = rewrite
        parts.append("")
        parts.append("## Rewritten version")
        parts.append("")
        parts.append(f"```{lang}")
        parts.append(body.rstrip())
        parts.append("```")
        if diff_text:
            parts.append("")
            parts.append(f"## Diff vs `{source_label}`")
            parts.append("")
            parts.append("```diff")
            parts.append(diff_text.rstrip())
            parts.append("```")
    return "\n".join(parts).rstrip() + "\n"


def render_to_stdout(
    console: Console,
    sections_1_3: str,
    rewrite: tuple[str, str] | None,
    diff_text: str,
    source_label: str,
) -> None:
    """Render the report to a Console.

    Uses rich's Markdown renderer for sections 1-3 (so headings, bullets, and
    any fenced snippets in the review itself get the rich treatment), then
    Syntax(..., lang) for the rewrite (proper highlighting + line numbers)
    and Syntax(..., "diff") for the unified diff. Console auto-disables ANSI
    when not a TTY, so `... | cat` produces clean text."""
    console.print(Markdown(sections_1_3))
    if rewrite is not None:
        body, lang = rewrite
        console.print()
        console.rule(f"[bold]Rewritten version[/bold] ({lang})")
        console.print()
        console.print(
            Syntax(body.rstrip(), lang, theme="monokai", line_numbers=True),
        )
        if diff_text:
            console.print()
            console.rule(f"[bold]Diff vs {source_label}[/bold]")
            console.print()
            console.print(
                Syntax(
                    diff_text.rstrip(), "diff", theme="monokai",
                    line_numbers=False,
                ),
            )


# --- CLI --------------------------------------------------------------------


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument(
    "source",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
)
@click.option(
    "-m", "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Ollama model name.",
)
@click.option(
    "-p", "--prompt",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Path to a markdown file whose contents replace the built-in "
        "system prompt (sections 1-3)."
    ),
)
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the report to this markdown file instead of stdout.",
)
@click.option(
    "--rewrite-prompt",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Optional path to a markdown file overriding the built-in rewrite "
        "prompt (section 4). Implies --with-rewrite."
    ),
)
@click.option(
    "--with-rewrite",
    is_flag=True,
    help=(
        "Also ask the model to produce a rewritten version (section 4) "
        "and a unified diff against the original source."
    ),
)
@click.option(
    "--host",
    default=DEFAULT_HOST,
    show_default=True,
    help="Ollama base URL.",
)
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help="Per-call HTTP timeout in seconds.",
)
def main(
    source: Path,
    model: str,
    prompt: Path | None,
    output: Path | None,
    rewrite_prompt: Path | None,
    with_rewrite: bool,
    host: str,
    timeout: int,
) -> None:
    """Review a source file with a local Ollama model."""
    try:
        _run(
            source=source,
            model=model,
            prompt=prompt,
            output=output,
            rewrite_prompt=rewrite_prompt,
            with_rewrite=with_rewrite,
            host=host,
            timeout=timeout,
        )
    except CodeReviewError as e:
        click.echo(f"code_review: {e}", err=True)
        raise SystemExit(1)


def _run(
    *,
    source: Path,
    model: str,
    prompt: Path | None,
    output: Path | None,
    rewrite_prompt: Path | None,
    with_rewrite: bool,
    host: str,
    timeout: int,
) -> None:
    if not source.is_file():
        raise CodeReviewError(f"not a readable file: {source}")
    try:
        source_text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try lossy so very long binary-ish files don't trip us.
        source_text = source.read_text(encoding="utf-8", errors="replace")

    review_prompt = load_prompt(prompt, REVIEW_PROMPT_MD)
    rewrite_prompt_text = load_prompt(rewrite_prompt, REWRITE_PROMPT)

    client = ollama.Client(host=host, timeout=timeout)

    # Stderr console for the spinner — keeps the spinner out of stdout so
    # piped runs (`... | cat`) don't get ANSI codes polluting the report.
    spinner_console = Console(stderr=True)
    sections = review_sections_1_3(
        client, model, review_prompt, source_text, spinner_console,
    )

    rewrite_block: tuple[str, str] | None = None
    diff_text = ""
    if with_rewrite or rewrite_prompt is not None:
        with spinner_console.status(
            f"[bold cyan]asking {model} for a rewrite...[/bold cyan]",
        ):
            user_msg = (
                "Here is the file to rewrite. Fix bugs, improve efficiency "
                "and readability, and return the full rewritten version.\n\n"
                "```\n" + source_text + "\n```\n"
            )
            result = _call(client, model, rewrite_prompt_text, user_msg)
            rewrite_block = extract_rewrite_block(result)
            if rewrite_block and rewrite_block[0]:
                diff_text = unified_diff_text(
                    source_text, rewrite_block[0], source.name,
                )

    if output is None:
        # stdout console — rich auto-disables ANSI when stdout isn't a TTY.
        stdout_console = Console()
        render_to_stdout(
            stdout_console, sections, rewrite_block, diff_text, source.name,
        )
    else:
        report = build_report_md(sections, rewrite_block, diff_text, source.name)
        output.write_text(report, encoding="utf-8")
        click.echo(f"[code_review] wrote {output}", err=True)


if __name__ == "__main__":
    main()

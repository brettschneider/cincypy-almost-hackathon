#!/usr/bin/env python3
"""CincyPy "Almost Hackathon" reference solution — stdlib-only GUI.

Same Ollama plumbing and prompts as
[solutions/cli-ollama-stdlib/code_review.py](../cli-ollama-stdlib/code_review.py),
wrapped in a tkinter GUI. The Ollama REST call, the system prompts, and the
rewrite-block extraction are imported from the CLI sibling so the two
reference solutions stay in lockstep on what they ask the model to produce.

    python code_review_gui.py

UI: pick a file, pick a model, hit Run. The model's review appears verbatim
in the right pane (markdown headings stay as `## …`, bullets stay as `- …` —
no rendering layer to debug). Tick "Rewrite" to also get section 4 in its
own tab. "Save Report…" writes the same markdown shape as the CLI's `-o`.

Why verbatim? At a hackathon the interesting question is what the model
*said*, not how the UI fluffed it. Showing the raw text makes it obvious
when the model drifted off-prompt — easier to coach, easier to fix.

Coach notes:
- Ollama must be running (`ollama serve`). If not, the status bar shows
  "Could not reach Ollama at <host>. Is `ollama serve` running?"
- The default model must be pulled (`ollama pull qwen3.5:4b`). If not, the
  status bar shows "is the model pulled? Try `ollama pull <model>`."
- Calls run on a worker thread so the window stays responsive. Status flips
  to "working…" while the model thinks; UI updates arrive via a queue poll.
"""

from __future__ import annotations

# --- sibling import shim ---------------------------------------------------
# The CLI sibling lives at ../cli-ollama-stdlib/code_review.py. Python package
# names can't contain hyphens, so the dir isn't a real package and the normal
# `from cli_ollama_stdlib.code_review import …` form won't work. Load it by
# file path with importlib instead — same module object, same attributes,
# just without a package namespace.
#
# Why bother? Sharing the Ollama REST plumbing and the system prompts keeps
# this GUI in lockstep with the CLI. If a coach tweaks the CLI prompt,
# attendees running the GUI get the same prompt automatically.

import importlib.util
import pathlib
import sys

_sibling_path = (
    pathlib.Path(__file__).resolve().parent.parent
    / "cli-ollama-stdlib" / "code_review.py"
)
if not _sibling_path.is_file():
    raise ImportError(
        f"expected sibling module at {_sibling_path}; "
        "the CLI reference solution must sit next to this one."
    )

_sibling_spec = importlib.util.spec_from_file_location(
    "cli_ollama_stdlib_sibling", _sibling_path,
)
_sibling = importlib.util.module_from_spec(_sibling_spec)
# Register before exec so @dataclass (which looks cls.__module__ up in
# sys.modules) finds it. Without this, dataclass raises AttributeError on
# Python 3.14+ for modules loaded by spec.
sys.modules[_sibling_spec.name] = _sibling
assert _sibling_spec.loader is not None
_sibling_spec.loader.exec_module(_sibling)

# Pull what we need into our namespace.
DEFAULT_MODEL = _sibling.DEFAULT_MODEL
DEFAULT_HOST = _sibling.DEFAULT_HOST
DEFAULT_TIMEOUT = _sibling.DEFAULT_TIMEOUT
REVIEW_PROMPT_MD = _sibling.REVIEW_PROMPT_MD
REWRITE_PROMPT = _sibling.REWRITE_PROMPT
CodeReviewError = _sibling.CodeReviewError
call_ollama = _sibling.call_ollama
extract_rewrite_block = _sibling.extract_rewrite_block

# --- stdlib imports ---------------------------------------------------------

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# A few common local models so the dropdown is useful without typing.
# Anything in here is just a starting point — the combobox is editable.
MODEL_CHOICES = (
    "qwen3.5:4b",
    "qwen3.5:7b",
    "llama3.2:3b",
    "gemma3:4b",
    "deepseek-coder:6.7b",
)


# --- worker thread ----------------------------------------------------------

def run_review(
    source_text: str,
    host: str,
    model: str,
    want_rewrite: bool,
    timeout: int,
    out: queue.Queue,
) -> None:
    """Worker body. Runs on a background thread. Posts events to `out`.

    Events are tuples: ("status", str) | ("sections", str) | ("rewrite", body, lang)
    | ("error", str). The UI thread drains `out` via root.after() and
    dispatches each event. The worker itself never touches tkinter.
    """
    try:
        out.put(("status", f"reviewing with {model}..."))
        user_msg = (
            "Please review this source file:\n\n"
            "```\n" + source_text + "\n```\n"
        )
        result = call_ollama(host, model, REVIEW_PROMPT_MD, user_msg, timeout)
        sections = result.text.strip()
        out.put(("sections", sections))

        if want_rewrite:
            out.put(("status", f"asking {model} for a rewrite..."))
            user_msg = (
                "Here is the file to rewrite. Fix bugs, improve efficiency "
                "and readability, and return the full rewritten version.\n\n"
                "```\n" + source_text + "\n```\n"
            )
            result = call_ollama(host, model, REWRITE_PROMPT, user_msg, timeout)
            body, lang = extract_rewrite_block(result.text.strip())
            if not body:
                raise CodeReviewError(
                    "model did not return a fenced rewrite block."
                )
            out.put(("rewrite", body, lang))

        out.put(("status", "done"))
    except Exception as e:
        # CodeReviewError carries a clean message; anything else gets wrapped
        # so the UI thread never sees an opaque traceback.
        msg = str(e) if isinstance(e, CodeReviewError) else f"{type(e).__name__}: {e}"
        out.put(("error", msg))


# --- save-report assembly ---------------------------------------------------

def build_report_md(sections: str, rewrite: tuple[str, str] | None) -> str:
    """Same shape as cli-ollama-stdlib.build_report_md — kept in sync by hand.

    Inlining (rather than importing) avoids pulling the CLI's _run/argparse
    surface into the GUI process. Twelve lines, easy to read at a glance.
    """
    parts = [sections.rstrip()]
    if rewrite is not None:
        body, lang = rewrite
        parts.append("")
        parts.append("## Rewritten version")
        parts.append("")
        parts.append(f"```{lang}")
        parts.append(body.rstrip())
        parts.append("```")
    return "\n".join(parts).rstrip() + "\n"


# --- app --------------------------------------------------------------------

class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue = queue.Queue()

        # State held outside widgets so worker thread can see it cleanly.
        self.worker: threading.Thread | None = None
        self.sections_text: str = ""
        self.rewrite_body: str = ""
        self.rewrite_lang: str = ""

        root.title("CincyPy Code Review")
        root.geometry("1100x720")
        root.minsize(800, 500)

        self._build_control_bar(root)
        self._build_body(root)
        self._build_status_bar(root)

        # Start the queue poller. It re-arms itself via after() so it runs
        # for the lifetime of the window. Coalescing at 100ms keeps the UI
        # smooth without flooding the event loop on long streams.
        self.root.after(100, self._poll_events)

    # -- layout --------------------------------------------------------------

    def _build_control_bar(self, root: tk.Tk) -> None:
        bar = ttk.Frame(root, padding=(8, 8, 8, 4))
        bar.pack(side=tk.TOP, fill=tk.X)

        # Row 1: file picker.
        row1 = ttk.Frame(bar)
        row1.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(row1, text="File:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        file_entry = ttk.Entry(row1, textvariable=self.file_var)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(row1, text="Browse…", command=self._on_browse).pack(side=tk.LEFT)
        # When the user picks a file, reflect it in the source preview.
        self.file_var.trace_add("write", lambda *_: self._refresh_source_preview())

        # Row 2: model, host, rewrite, run, save.
        row2 = ttk.Frame(bar)
        row2.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

        ttk.Label(row2, text="Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        model_combo = ttk.Combobox(
            row2,
            textvariable=self.model_var,
            values=MODEL_CHOICES,
            width=24,
        )
        # state="normal" so the user can type a model name not in MODEL_CHOICES.
        model_combo.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Label(row2, text="Host:").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        ttk.Entry(row2, textvariable=self.host_var, width=30).pack(
            side=tk.LEFT, padx=(6, 12)
        )

        self.rewrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Rewrite", variable=self.rewrite_var).pack(
            side=tk.LEFT, padx=(0, 12)
        )

        self.run_btn = ttk.Button(row2, text="Run", command=self._on_run)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.save_btn = ttk.Button(
            row2, text="Save Report…", command=self._on_save, state=tk.DISABLED,
        )
        self.save_btn.pack(side=tk.LEFT)

    def _build_body(self, root: tk.Tk) -> None:
        # Horizontal paned split: source on the left, notebook on the right.
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Source preview — read-only monospace text. Wrapping off so line
        # numbers / indentation match what the model sees.
        src_frame = ttk.LabelFrame(paned, text="Source")
        self.src_text = tk.Text(
            src_frame,
            wrap=tk.NONE,
            font=("Menlo", 11) if _have_menlo() else ("Courier", 11),
            state=tk.DISABLED,
            undo=False,
        )
        src_scroll_y = ttk.Scrollbar(src_frame, orient=tk.VERTICAL, command=self.src_text.yview)
        src_scroll_x = ttk.Scrollbar(src_frame, orient=tk.HORIZONTAL, command=self.src_text.xview)
        self.src_text.configure(yscrollcommand=src_scroll_y.set, xscrollcommand=src_scroll_x.set)
        self.src_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        src_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        src_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        paned.add(src_frame, weight=1)

        # Right side: notebook with Review and Rewrite tabs.
        self.notebook = ttk.Notebook(paned)
        paned.add(self.notebook, weight=2)

        self.review_text = self._make_text_tab(self.notebook, "Review")
        self.rewrite_text = self._make_text_tab(self.notebook, "Rewrite")
        # Rewrite tab is disabled until we have something to show. The tab
        # itself stays visible (so the user knows the option exists) but
        # can't be clicked into.
        self._set_rewrite_tab_state(tk.DISABLED)

    def _make_text_tab(self, notebook: ttk.Notebook, title: str) -> tk.Text:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        text = tk.Text(
            frame,
            wrap=tk.WORD,
            font=("Menlo", 11) if _have_menlo() else ("Courier", 11),
            undo=False,
        )
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        return text

    def _build_status_bar(self, root: tk.Tk) -> None:
        self.status_var = tk.StringVar(value="idle — pick a file and press Run.")
        bar = ttk.Frame(root, padding=(8, 4, 8, 8))
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(bar, textvariable=self.status_var, anchor=tk.W).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    # -- event handlers ------------------------------------------------------

    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(title="Pick a source file to review")
        if path:
            self.file_var.set(path)

    def _refresh_source_preview(self) -> None:
        path_str = self.file_var.get().strip()
        self.src_text.configure(state=tk.NORMAL)
        self.src_text.delete("1.0", tk.END)
        if path_str:
            try:
                text = pathlib.Path(path_str).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = pathlib.Path(path_str).read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                # Don't dump a stacktrace into the source pane; just show the
                # error and leave the rest blank. Run will re-validate.
                text = f"<could not read file: {e}>"
            except Exception:
                text = ""
        else:
            text = ""
        self.src_text.insert("1.0", text)
        self.src_text.configure(state=tk.DISABLED)

    def _on_run(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            # Already running — ignore the second click. Could add a Cancel
            # button later; for a coach demo, ignore is simpler.
            return

        path_str = self.file_var.get().strip()
        if not path_str:
            messagebox.showerror("No file", "Pick a source file first.")
            return
        src_path = pathlib.Path(path_str)
        if not src_path.is_file():
            messagebox.showerror("Not a file", f"{src_path} is not a readable file.")
            return
        try:
            source_text = src_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source_text = src_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            messagebox.showerror("Read failed", str(e))
            return

        host = self.host_var.get().strip() or DEFAULT_HOST
        model = self.model_var.get().strip() or DEFAULT_MODEL
        want_rewrite = bool(self.rewrite_var.get())

        # Reset prior output so a new run doesn't show stale text under a
        # fresh heading.
        self._set_text(self.review_text, "")
        self._set_text(self.rewrite_text, "")
        self._set_rewrite_tab_state(tk.DISABLED)
        self.sections_text = ""
        self.rewrite_body = ""
        self.rewrite_lang = ""
        self.save_btn.configure(state=tk.DISABLED)

        self.run_btn.configure(state=tk.DISABLED)
        self.status_var.set(f"reviewing with {model}...")

        self.worker = threading.Thread(
            target=run_review,
            args=(
                source_text, host, model, want_rewrite, DEFAULT_TIMEOUT,
                self.events,
            ),
            daemon=True,
        )
        self.worker.start()

    def _on_save(self) -> None:
        if not self.sections_text:
            messagebox.showinfo("Nothing to save", "Run a review first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save report",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return
        rewrite = (self.rewrite_body, self.rewrite_lang) if self.rewrite_body else None
        try:
            pathlib.Path(path).write_text(
                build_report_md(self.sections_text, rewrite),
                encoding="utf-8",
            )
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.status_var.set(f"saved → {path}")

    # -- queue / thread glue -------------------------------------------------

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "status":
            self.status_var.set(event[1])
        elif kind == "sections":
            self.sections_text = event[1]
            self._set_text(self.review_text, self.sections_text)
            self.save_btn.configure(state=tk.NORMAL)
        elif kind == "rewrite":
            _, body, lang = event
            self.rewrite_body = body
            self.rewrite_lang = lang
            header = f"```{lang}\n" if lang else ""
            self._set_text(self.rewrite_text, header + body + "\n```")
            self._set_rewrite_tab_state(tk.NORMAL)
        elif kind == "error":
            msg = event[1]
            self.status_var.set(f"error: {msg}")
            messagebox.showerror("Review failed", msg)
        if kind in ("done", "error"):
            self.run_btn.configure(state=tk.NORMAL)

    # -- small widget helpers ------------------------------------------------

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        # Review/rewrite panes stay editable so users can copy/edit; the
        # source pane is the only one we lock.
        widget.see("1.0")

    def _set_rewrite_tab_state(self, state: str) -> None:
        # Notebook.tab() takes a state option in ttk; "disabled" greys and
        # blocks selection, "normal" re-enables.
        try:
            self.notebook.tab(1, state=state)
        except tk.TclError:
            # If the notebook hasn't been built yet (shouldn't happen, but
            # be defensive), swallow — the tab will use the default state.
            pass


def _have_menlo() -> bool:
    """Return True if the 'Menlo' font is available — fall back to Courier.

    Menlo ships with macOS; on Linux/Windows it's missing and tkinter would
    silently substitute, but checking first gives a deterministic font on
    every platform.
    """
    try:
        import tkinter.font as tkfont
        return "Menlo" in tkfont.families()
    except Exception:
        return False


def main() -> int:
    root = tk.Tk()
    # ttk uses the platform's native theme; 'aqua' on macOS, 'vista' on
    # Windows, 'clam' on Linux. Picking nothing keeps the default — better
    # than hardcoding a theme that may not exist.
    try:
        style = ttk.Style()
        # Sanity-check that we got a real theme; on a stripped-down box this
        # can be empty, in which case fall back to 'clam'.
        if not style.theme_use():
            style.theme_use("clam")
    except tk.TclError:
        pass

    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

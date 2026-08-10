#!/usr/bin/env python3
"""CincyPy "Almost Hackathon" reference solution — third-party + PySide6 GUI.

Same Ollama plumbing and prompts as
[solutions/cli-ollama-stdlib/code_review.py](../cli-ollama-stdlib/code_review.py),
wrapped in a PySide6 GUI. The Ollama REST call, the system prompts, and the
rewrite-block extraction are imported from the stdlib CLI sibling so all three
reference solutions (this, the stdlib GUI, and the stdlib CLI) stay in lockstep
on what they ask the model to produce.

    .venv/bin/python code_review_gui.py

What the third-party buys over the stdlib GUI (../gui-ollama-stdlib/):

- **PySide6** instead of tkinter — modern Qt widgets, native look on every
  platform, proper QSplitter, QSettings, QThread + Signal/Slot for the
  worker, no `after()` polling loop.
- **Pygments** syntax highlighting in the source preview, the rewrite pane,
  and the diff tab. Tkinter can fake it with tags; Pygments gives a real,
  lexer-accurate result with zero effort.
- **markdown-it-py** renders the review as proper formatted markdown in a
  QTextBrowser instead of dumping verbatim `## headings` and `- bullets`.
  The stdlib GUI was deliberately honest about raw model output; this one
  is deliberately polished.
- **httpx** replaces urllib for the Ollama call — clearer exception types
  (ConnectError, ReadTimeout) and clean connect/read timeout composition.
- **rich** is pulled in only for a nicer traceback if the worker ever
  raises. Everything visible to the user is native Qt.

UI: pick a file, pick a model, hit Run. The review renders as markdown on
the right. Tick "Rewrite" to also get section 4 (the rewritten file) plus a
unified diff against the original — each in its own tab. "Save Report…"
writes the same markdown shape as the CLI's `-o`.

Coach notes:
- Ollama must be running (`ollama serve`). If not, the status bar shows
  "Could not reach Ollama at <host>. Is `ollama serve` running?"
- The default model must be pulled (`ollama pull qwen3.5:4b`). If not, the
  status bar shows "is the model pulled? Try `ollama pull <model>`."
- Calls run on a QThread; status flips to "working…" while the model
  thinks; UI updates arrive via Qt signals.
"""

from __future__ import annotations

# --- sibling import shim ---------------------------------------------------
# The stdlib CLI sibling lives at ../cli-ollama-stdlib/code_review.py. Python
# package names can't contain hyphens, so the dir isn't a real package and
# the normal `from cli_ollama_stdlib.code_review import …` form won't work.
# Load it by file path with importlib instead — same module object, same
# attributes, just without a package namespace.
#
# Why bother? Sharing the Ollama REST plumbing and the system prompts keeps
# this GUI in lockstep with the stdlib CLI and the stdlib GUI. If a coach
# tweaks the CLI prompt, attendees running any of the reference solutions
# get the same prompt automatically.

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
        "the stdlib CLI reference solution must sit next to this one."
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

# --- third-party imports ----------------------------------------------------

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import (
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import httpx
import markdown_it
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import (
    DiffLexer,
    TextLexer,
    get_lexer_by_name,
    guess_lexer,
)
from pygments.util import ClassNotFound
from rich.traceback import install as rich_install

# A few common local models so the dropdown is useful without typing.
# Anything in here is just a starting point — the combobox is editable.
MODEL_CHOICES = (
    "qwen3.5:4b",
    "qwen3.5:7b",
    "llama3.2:3b",
    "gemma3:4b",
    "deepseek-coder:6.7b",
)


# --- helpers: language guessing --------------------------------------------

def _guess_lang(source_path: pathlib.Path, source_text: str) -> str:
    """Pick a Pygments lexer name for a source file. Falls back to 'text'.

    Filename extension beats content sniffing for the common cases
    (`.py` → `python`, `.js` → `javascript`); content sniffing catches
    the unusual ones (no extension, weird extension)."""
    try:
        return get_lexer_by_name(_guess_lang_from_ext(source_path), stripall=True).name.lower()
    except ClassNotFound:
        pass
    try:
        return guess_lexer(source_text).name.lower()
    except ClassNotFound:
        return "text"


def _guess_lang_from_ext(source_path: pathlib.Path) -> str:
    """Map file extension to a Pygments lexer short name."""
    ext = source_path.suffix.lstrip(".").lower()
    return {
        "py": "python",
        "pyi": "python",
        "js": "javascript",
        "mjs": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "jsx": "jsx",
        "rb": "ruby",
        "go": "go",
        "rs": "rust",
        "java": "java",
        "kt": "kotlin",
        "swift": "swift",
        "c": "c",
        "h": "c",
        "cpp": "cpp",
        "cc": "cpp",
        "hpp": "cpp",
        "cs": "csharp",
        "php": "php",
        "sh": "bash",
        "bash": "bash",
        "zsh": "bash",
        "html": "html",
        "htm": "html",
        "css": "css",
        "scss": "scss",
        "sql": "sql",
        "md": "markdown",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
    }.get(ext, ext or "text")


# --- Pygments syntax highlighter -------------------------------------------
# QSyntaxHighlighter takes a QTextDocument and applies formats as it lays
# out each line. Pygments does the tokenizing; we translate its token
# classes into QTextCharFormat objects and tag the line.

# Map a subset of Pygments token types to Qt text formats. Only the types
# that actually appear in code are mapped — anything else gets the default
# (plain) format. Format objects are created once and reused.

_PYG_TO_FORMAT: dict[str, QTextCharFormat] = {}


def _pyg_format(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    """Build a QTextCharFormat for a Pygments token class.

    Color is a #rrggbb string. Bold/italic are common shortcuts for token
    classes like Keyword.Reserved (bold) or Comment (italic)."""
    fmt = QTextCharFormat()
    fmt.setForeground(_hex_color(color))
    if bold:
        fmt.setFontWeight(QFont.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


def _hex_color(s: str):
    """Lazy import so the module loads even on a Qt-less CI smoke test."""
    from PySide6.QtGui import QColor
    return QColor(s)


def _init_pyg_formats() -> None:
    """Build the token-class → QTextCharFormat table once."""
    global _PYG_TO_FORMAT
    if _PYG_TO_FORMAT:
        return
    _PYG_TO_FORMAT = {
        "Keyword":              _pyg_format("#000080", bold=True),
        "Keyword.Constant":     _pyg_format("#000080", bold=True),
        "Keyword.Declaration":  _pyg_format("#000080", bold=True),
        "Keyword.Namespace":    _pyg_format("#000080", bold=True),
        "Keyword.Reserved":     _pyg_format("#000080", bold=True),
        "Keyword.Type":         _pyg_format("#0086b3", bold=True),
        "Name":                 _pyg_format("#000000"),
        "Name.Function":        _pyg_format("#006400"),
        "Name.Class":           _pyg_format("#006400", bold=True),
        "Name.Decorator":       _pyg_format("#aa22ff"),
        "Name.Builtin":         _pyg_format("#0086b3"),
        "Name.Builtin.Pseudo":  _pyg_format("#0086b3"),
        "Name.Variable":        _pyg_format("#000000"),
        "Name.Variable.Magic":  _pyg_format("#aa22ff"),
        "Name.Constant":        _pyg_format("#aa22ff"),
        "String":               _pyg_format("#ba2121"),
        "String.Doc":           _pyg_format("#ba2121", italic=True),
        "String.Escape":        _pyg_format("#bb6622", bold=True),
        "Number":               _pyg_format("#666666"),
        "Comment":              _pyg_format("#008000", italic=True),
        "Comment.Single":       _pyg_format("#008000", italic=True),
        "Comment.Multiline":    _pyg_format("#008000", italic=True),
        "Operator":             _pyg_format("#666666"),
        "Operator.Word":        _pyg_format("#aa22ff", bold=True),
        "Punctuation":         _pyg_format("#666666"),
        "Error":                _pyg_format("#ff0000", bold=True),
        "Generic.Heading":      _pyg_format("#000080", bold=True),
        "Generic.Subheading":   _pyg_format("#008080"),
        "Generic.Emph":         _pyg_format("#000000", italic=True),
        "Generic.Strong":       _pyg_format("#000000", bold=True),
    }


def _format_for_token(token_type: str) -> QTextCharFormat | None:
    """Look up the QTextCharFormat for a Pygments token type.

    Walks the dotted prefix: "Comment.Single" matches "Comment" if no more
    specific entry exists, then "Comment" itself, then "" (plain)."""
    cur = token_type
    while cur:
        if cur in _PYG_TO_FORMAT:
            return _PYG_TO_FORMAT[cur]
        if "." not in cur:
            break
        cur = cur.rsplit(".", 1)[0]
    return None


class PygmentsHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter that defers to a Pygments lexer.

    `lexer_name` is a Pygments lexer short name ('python', 'javascript',
    'diff', etc.). Call set_language() to swap lexers without rebuilding
    the widget — used when the user picks a new file."""

    def __init__(self, doc, lexer_name: str = "text") -> None:
        super().__init__(doc)
        _init_pyg_formats()
        self.set_language(lexer_name)

    def set_language(self, lexer_name: str) -> None:
        try:
            self._lexer = get_lexer_by_name(lexer_name, stripall=True)
        except ClassNotFound:
            self._lexer = TextLexer()
        # Rehighlight the whole document so a lexer swap is visible
        # immediately rather than only on the next edit.
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
        # Pygments' lex() takes (text, stack) and yields (tokentype, value)
        # tuples for the line. For each non-empty chunk we apply the
        # matching format starting at the current cursor position.
        start = 0
        for tokentype, value in self._lexer.get_tokens(text):
            if not value:
                continue
            length = len(value)
            fmt = _format_for_token(str(tokentype))
            if fmt is not None:
                self.setFormat(start, length, fmt)
            start += length


def render_code_html(text: str, lexer_name: str) -> str:
    """Highlight `text` with the named Pygments lexer and return HTML.

    Used for the QTextBrowser "Source" tab — the html() output goes into
    QTextBrowser.setHtml() which understands a subset of HTML."""
    try:
        lexer = get_lexer_by_name(lexer_name, stripall=True)
    except ClassNotFound:
        lexer = TextLexer()
    formatter = HtmlFormatter(
        full=True, noclasses=True,
        style="default", linenos="table",
    )
    return highlight(text, lexer, formatter)


def render_markdown_html(md_text: str) -> str:
    """Render markdown to an HTML fragment for QTextBrowser.

    markdown-it-py is CommonMark+GFM-compliant; the resulting HTML is
    dropped into QTextBrowser with a small style block so headings,
    bullets, and code fences all read correctly."""
    md = markdown_it.MarkdownIt("commonmark", {"html": False, "breaks": False})
    body = md.render(md_text)
    return (
        "<style>"
        "body { font-family: -apple-system, sans-serif; }"
        "h2 { color: #1a4480; margin-top: 1.2em; }"
        "h3 { color: #2a5aa8; margin-top: 1.0em; }"
        "code { background: #f4f4f4; padding: 0 4px; border-radius: 3px; }"
        "pre  { background: #f4f4f4; padding: 8px; border-radius: 4px; }"
        "li   { margin-bottom: 0.2em; }"
        "</style>"
        + body
    )


def render_diff_html(diff_text: str) -> str:
    """Highlight a unified diff with Pygments' DiffLexer."""
    formatter = HtmlFormatter(
        full=True, noclasses=True,
        style="default", linenos=False,
    )
    return highlight(diff_text, DiffLexer(), formatter)


# --- worker thread ---------------------------------------------------------

class ReviewWorker(QThread):
    """QThread that calls Ollama and emits results back to the UI.

    Signals:
        status(str)   — human-readable progress line for the status bar.
        sections(str) — markdown text of sections 1-3.
        rewrite(str, str) — (body, lang) of the rewritten file.
        diff(str)     — unified diff between original source and rewrite.
        error(str)    — user-facing error message; always terminal.
        done()        — terminal signal on either success or error.

    The worker never touches Qt widgets directly; it only emits signals,
    and the main window connects slots. This is the canonical Qt threading
    pattern and avoids the `after()` polling loop the stdlib GUI uses."""

    status = Signal(str)
    sections = Signal(str)
    rewrite = Signal(str, str)
    diff = Signal(str)
    error = Signal(str)
    done = Signal()

    def __init__(
        self,
        *,
        source_text: str,
        source_label: str,
        host: str,
        model: str,
        want_rewrite: bool,
        timeout: int,
    ) -> None:
        super().__init__()
        self.source_text = source_text
        self.source_label = source_label
        self.host = host
        self.model = model
        self.want_rewrite = want_rewrite
        self.timeout = timeout

    def run(self) -> None:
        try:
            self.status.emit(f"reviewing with {self.model}...")
            user_msg = (
                "Please review this source file:\n\n"
                "```\n" + self.source_text + "\n```\n"
            )
            result = call_ollama(
                self.host, self.model,
                REVIEW_PROMPT_MD, user_msg, self.timeout,
            )
            self.sections.emit(result.text.strip())

            if self.want_rewrite:
                self.status.emit(f"asking {self.model} for a rewrite...")
                user_msg = (
                    "Here is the file to rewrite. Fix bugs, improve "
                    "efficiency and readability, and return the full "
                    "rewritten version.\n\n"
                    "```\n" + self.source_text + "\n```\n"
                )
                result = call_ollama(
                    self.host, self.model,
                    REWRITE_PROMPT, user_msg, self.timeout,
                )
                body, lang = extract_rewrite_block(result.text.strip())
                if not body:
                    raise CodeReviewError(
                        "model did not return a fenced rewrite block."
                    )
                self.rewrite.emit(body, lang)

                # Diff against the original. Use difflib (stdlib) — no
                # need for another package. Emit even when the diff is
                # empty (model returned identical source) so the tab is
                # available.
                import difflib
                diff = "".join(
                    difflib.unified_diff(
                        self.source_text.splitlines(keepends=True),
                        body.splitlines(keepends=True),
                        fromfile=self.source_label,
                        tofile=f"{self.source_label} (rewritten)",
                        lineterm="",
                    )
                )
                self.diff.emit(diff)

            self.status.emit("done")
            self.done.emit()
        except Exception as e:
            msg = (
                str(e) if isinstance(e, CodeReviewError)
                else f"{type(e).__name__}: {e}"
            )
            self.error.emit(msg)
            self.done.emit()


# --- save-report assembly --------------------------------------------------

def build_report_md(
    sections: str,
    rewrite: tuple[str, str] | None,
    diff_text: str,
    source_label: str,
) -> str:
    """Same shape as cli-ollama-3rd-party.build_report_md — markdown review
    + fenced rewrite + fenced diff. Kept in sync by hand."""
    parts = [sections.rstrip()]
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


# --- main window ----------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CincyPy Code Review")
        self.resize(1200, 760)
        self.setMinimumSize(900, 540)

        # Held outside widgets so the worker can populate them.
        self.sections_md: str = ""
        self.rewrite_body: str = ""
        self.rewrite_lang: str = ""
        self.diff_text: str = ""
        self.worker: ReviewWorker | None = None

        self._build_ui()
        self._wire_signals()

        self._set_status("idle — pick a file and press Run.")

    # -- layout --------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 4)
        outer.setSpacing(6)

        outer.addLayout(self._build_controls())

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, stretch=1)

        # Left: source preview (plain text + Pygments highlighter).
        src_widget, self.src_view = self._make_code_view(
            splitter, "Source", editable=False,
        )
        self.src_highlighter = PygmentsHighlighter(self.src_view.document(), "text")
        splitter.addWidget(src_widget)

        # Right: tabbed view — Review (rendered markdown), Rewrite
        # (highlighted code), Diff (highlighted unified diff).
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.review_view = QTextBrowser()
        self.review_view.setOpenExternalLinks(False)
        self.review_view.document().setDefaultStyleSheet(
            "h2 { color: #1a4480; margin-top: 1.2em; }"
            "h3 { color: #2a5aa8; margin-top: 1.0em; }"
            "code { background: #f4f4f4; padding: 0 4px; border-radius: 3px; }"
            "pre  { background: #f4f4f4; padding: 8px; border-radius: 4px; }"
            "li   { margin-bottom: 0.2em; }"
        )
        self.tabs.addTab(self.review_view, "Review")

        # Rewrite & Diff tabs are built lazily (they need a known lexer for
        # highlighting). We add placeholder widgets here and replace them
        # once we know the language.
        self.rewrite_placeholder = QWidget()
        self.tabs.addTab(self.rewrite_placeholder, "Rewrite")
        self.diff_placeholder = QWidget()
        self.tabs.addTab(self.diff_placeholder, "Diff")
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

        # Status bar at the bottom.
        self.setStatusBar(QStatusBar(self))
        self._status_label = QLabel()
        self.statusBar().addWidget(self._status_label, stretch=1)

    def _build_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        row.addWidget(QLabel("File:"))
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Pick a source file…")
        row.addWidget(self.file_edit, stretch=1)
        self.browse_btn = QPushButton("Browse…")
        row.addWidget(self.browse_btn)

        row.addSpacing(12)
        row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(MODEL_CHOICES)
        self.model_combo.setCurrentText(DEFAULT_MODEL)
        self.model_combo.setMinimumWidth(180)
        row.addWidget(self.model_combo)

        row.addSpacing(12)
        row.addWidget(QLabel("Host:"))
        self.host_edit = QLineEdit(DEFAULT_HOST)
        self.host_edit.setMinimumWidth(220)
        row.addWidget(self.host_edit)

        self.rewrite_check = QCheckBox("Rewrite")
        row.addWidget(self.rewrite_check)

        self.run_btn = QPushButton("Run")
        self.run_btn.setDefault(True)
        row.addWidget(self.run_btn)

        self.save_btn = QPushButton("Save Report…")
        self.save_btn.setEnabled(False)
        row.addWidget(self.save_btn)

        return row

    def _make_code_view(
        self, parent: QWidget, title: str, *, editable: bool,
    ) -> tuple[QWidget, QPlainTextEdit]:
        """Build a labeled plain-text view with a vertical scroll bar.

        QPlainTextEdit is the right choice for source/rewrite/diff panes:
        QTextEdit wraps by default, QPlainTextEdit doesn't, so line numbers
        and indentation stay aligned."""
        wrapper = QWidget(parent)
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(QLabel(title))

        edit = QPlainTextEdit()
        edit.setReadOnly(not editable)
        edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont("Menlo", 11)
        if not _have_menlo():
            font = QFont("Courier", 11)
        edit.setFont(font)
        v.addWidget(edit, stretch=1)
        return wrapper, edit

    def _wire_signals(self) -> None:
        self.browse_btn.clicked.connect(self._on_browse)
        self.file_edit.textChanged.connect(self._refresh_source_preview)
        self.run_btn.clicked.connect(self._on_run)
        self.save_btn.clicked.connect(self._on_save)

    # -- event handlers ------------------------------------------------------

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Pick a source file to review",
        )
        if path:
            self.file_edit.setText(path)

    def _refresh_source_preview(self) -> None:
        path_str = self.file_edit.text().strip()
        self.src_view.setPlainText("")
        if not path_str:
            self.src_highlighter.set_language("text")
            return
        path = pathlib.Path(path_str)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                self.src_view.setPlainText(f"<could not read file: {e}>")
                self.src_highlighter.set_language("text")
                return
        except OSError as e:
            self.src_view.setPlainText(f"<could not read file: {e}>")
            self.src_highlighter.set_language("text")
            return
        self.src_view.setPlainText(text)
        self.src_highlighter.set_language(_guess_lang(path, text))

    def _on_run(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return

        path_str = self.file_edit.text().strip()
        if not path_str:
            QMessageBox.critical(self, "No file", "Pick a source file first.")
            return
        src_path = pathlib.Path(path_str)
        if not src_path.is_file():
            QMessageBox.critical(self, "Not a file", f"{src_path} is not a readable file.")
            return
        try:
            source_text = src_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source_text = src_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            QMessageBox.critical(self, "Read failed", str(e))
            return

        host = self.host_edit.text().strip() or DEFAULT_HOST
        model = self.model_combo.currentText().strip() or DEFAULT_MODEL
        want_rewrite = self.rewrite_check.isChecked()

        # Reset prior output so a new run doesn't show stale text under a
        # fresh heading.
        self.sections_md = ""
        self.rewrite_body = ""
        self.rewrite_lang = ""
        self.diff_text = ""
        self.review_view.clear()
        self._replace_tab(1, QLabel("(no rewrite yet — tick 'Rewrite' and re-run)"), "Rewrite")
        self._replace_tab(2, QLabel("(no diff yet — tick 'Rewrite' and re-run)"), "Diff")
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.save_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self._set_status(f"reviewing with {model}...")

        self.worker = ReviewWorker(
            source_text=source_text,
            source_label=src_path.name,
            host=host,
            model=model,
            want_rewrite=want_rewrite,
            timeout=DEFAULT_TIMEOUT,
        )
        # Qt's signal/slot wiring replaces the stdlib GUI's queue + after()
        # polling. Each signal fires once on the UI thread (Qt guarantees
        # this when the worker is a QThread and slots are on the window).
        self.worker.status.connect(self._set_status)
        self.worker.sections.connect(self._on_sections)
        self.worker.rewrite.connect(self._on_rewrite)
        self.worker.diff.connect(self._on_diff)
        self.worker.error.connect(self._on_error)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_save(self) -> None:
        if not self.sections_md:
            QMessageBox.information(
                self, "Nothing to save", "Run a review first.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save report",
            "code_review_report.md",
            "Markdown (*.md);;All files (*)",
        )
        if not path:
            return
        rewrite = (
            (self.rewrite_body, self.rewrite_lang)
            if self.rewrite_body else None
        )
        try:
            pathlib.Path(path).write_text(
                build_report_md(
                    self.sections_md, rewrite, self.diff_text,
                    pathlib.Path(self.file_edit.text()).name,
                ),
                encoding="utf-8",
            )
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return
        self._set_status(f"saved → {path}")

    # -- worker slots --------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _on_sections(self, sections_md: str) -> None:
        self.sections_md = sections_md
        self.review_view.setHtml(render_markdown_html(sections_md))
        self.save_btn.setEnabled(True)

    def _on_rewrite(self, body: str, lang: str) -> None:
        self.rewrite_body = body
        self.rewrite_lang = lang
        # Build a real QPlainTextEdit with a Pygments highlighter for the
        # rewrite. This replaces the placeholder tab added in _build_ui.
        view_widget, view = self._make_code_view(self, "", editable=True)
        view.setPlainText(body)
        PygmentsHighlighter(view.document(), lang or "text")
        self._replace_tab(1, view_widget, "Rewrite")
        self.tabs.setTabEnabled(1, True)

    def _on_diff(self, diff_text: str) -> None:
        self.diff_text = diff_text
        view_widget, view = self._make_code_view(self, "", editable=False)
        view.setPlainText(diff_text or "(no changes)")
        PygmentsHighlighter(view.document(), "diff")
        self._replace_tab(2, view_widget, "Diff")
        self.tabs.setTabEnabled(2, True)

    def _on_error(self, msg: str) -> None:
        self._set_status(f"error: {msg}")
        QMessageBox.critical(self, "Review failed", msg)

    def _on_done(self) -> None:
        self.run_btn.setEnabled(True)
        self.worker = None

    # -- small widget helpers ------------------------------------------------

    def _replace_tab(self, index: int, widget: QWidget, label: str) -> None:
        """Swap out the widget at `index` for `widget`, keeping the label.

        QTabWidget takes ownership of any widget removed with removeTab(),
        so we have to delete it to avoid leaking."""
        old = self.tabs.widget(index)
        if old is not None:
            self.tabs.removeTab(index)
            old.deleteLater()
        self.tabs.insertTab(index, widget, label)
        self.tabs.setCurrentIndex(index)


def _have_menlo() -> bool:
    """Return True if the 'Menlo' font is available — fall back to Courier.

    Menlo ships with macOS; on Linux/Windows it's missing and Qt would
    silently substitute, but checking first gives a deterministic font on
    every platform."""
    from PySide6.QtGui import QFontDatabase
    return "Menlo" in QFontDatabase.families()


def main() -> int:
    # Install rich's traceback handler so any uncaught exception in the
    # worker shows up with local variables and source context if it ever
    # escapes our except block. Cheap; never visible in normal operation.
    rich_install(show_locals=False)

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
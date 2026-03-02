"""UI renderers for responses and events.

This module handles converting agent responses and events into NiceGUI components
with theme-aware styling.
"""

import html as html_escape
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from agex.agent.events import FileEvent
from agex.agent.datatypes import EditAction, FileAction
from agex_ui.core.responses import (
    DataFramePart,
    PlotlyPart,
    Response,
    ResponsePart,
    TextPart,
)


@dataclass
class PartRenderer:
    """Renders individual parts to NiceGUI components with theme support.

    All render methods use CSS variables from theme.py for consistent styling.
    """

    def render_text(self, text: str):
        """Render markdown text with theme-aware styling."""
        ui.markdown(
            text, extras=["fenced-code-blocks", "tables", "cuddled-lists"]
        ).classes("w-full").style("margin: 0;")

    def render_dataframe(self, df: pd.DataFrame):
        """Render pandas DataFrame as a themed table."""
        with (
            ui.element("div")
            .classes("w-full overflow-x-auto overflow-y-auto")
            .style(
                "margin-top: 0.75em; margin-bottom: 0.75em; "
                "max-height: 400px;"  # Limit height, scroll for long tables
            )
        ):
            ui.table.from_pandas(df).classes("w-full themed-table").style(
                "min-width: 0"
            ).props("auto-width wrap-cells flat bordered")

    def render_plotly(self, fig: go.Figure, dark_mode: bool = False):
        """Render Plotly figure with both light and dark versions.

        Renders two versions of the chart and uses CSS to show/hide based on theme.

        Args:
            fig: Plotly figure to render
            dark_mode: Initial theme (used for default visibility)
        """
        import copy
        import json

        # Sanitize figure to ensure JSON serializability
        # This converts pandas Timestamps and other non-JSON types to strings
        fig = go.Figure(json.loads(fig.to_json()))

        # Create deep copies for light and dark versions
        fig_light = copy.deepcopy(fig)
        fig_dark = copy.deepcopy(fig)

        # Configure light version - set explicit width for initial render
        if hasattr(fig_light, "update_layout"):
            fig_light.update_layout(
                template="plotly_white",
                paper_bgcolor="#ffffff",
                plot_bgcolor="#f6f8fa",
                autosize=True,
                margin=dict(l=40, r=40, t=40, b=40),
            )

        # Configure dark version
        if hasattr(fig_dark, "update_layout"):
            fig_dark.update_layout(
                template="plotly_dark",
                paper_bgcolor="#161b22",
                plot_bgcolor="#0d1117",
                autosize=True,
                margin=dict(l=40, r=40, t=40, b=40),
            )

        # Render both versions with theme-aware visibility
        with (
            ui.element("div")
            .classes("plotly-container w-full")
            .style(
                "overflow-x: auto; width: 100%; margin-top: 0.75em; margin-bottom: 0.75em;"
            )
        ):
            # Light mode chart (hidden in dark mode)
            ui.plotly(fig_light).classes("plotly-light-mode").style(
                "min-height: 350px; height: 350px; width: 100%;"
            )
            # Dark mode chart (hidden in light mode)
            ui.plotly(fig_dark).classes("plotly-dark-mode").style(
                "min-height: 350px; height: 350px; width: 100%;"
            )

    def render_code(self, code: str, language: str = "python"):
        """Render code with syntax highlighting using NiceGUI's code component."""
        if code.strip():
            ui.code(code, language=language).classes("w-full")

    def render_part(self, part: ResponsePart | Any, dark_mode: bool = False):
        """Render a single response part based on its type."""
        match part:
            case TextPart(content=text):
                self.render_text(text)
            case DataFramePart(df=df):
                self.render_dataframe(df)
            case PlotlyPart(figure=fig):
                self.render_plotly(fig, dark_mode=dark_mode)
            case str():
                self.render_text(part)
            case pd.DataFrame():
                self.render_dataframe(part)
            case go.Figure():
                self.render_plotly(part, dark_mode=dark_mode)
            case _:
                # Fallback: render as text
                self.render_text(str(part))


class ResponseRenderer:
    """Renders complete agent responses to NiceGUI components."""

    def __init__(self, dark_mode: bool = False):
        self.part_renderer = PartRenderer()
        self.dark_mode = dark_mode

    def render_response(self, response: str | pd.DataFrame | go.Figure | Response):
        """Render a complete response (handles mixed types).

        Args:
            response: Can be a single type (str, DataFrame, Figure) or a Response object
        """
        match response:
            case Response():
                # Wrap all parts in a single container to eliminate gaps
                # Force full width so charts/tables aren't constrained by text width
                with ui.element("div").classes("w-full").style(
                    "margin: 0; padding: 0; width: 100%; min-width: 100%;"
                ):
                    # Merge consecutive text parts to avoid gaps between them
                    normalized_parts = response.normalize()
                    merged_parts = []
                    text_buffer = []

                    for part in normalized_parts:
                        if isinstance(part, TextPart):
                            # Accumulate consecutive text parts
                            text_buffer.append(part.content)
                        else:
                            # Flush accumulated text before non-text part
                            if text_buffer:
                                merged_parts.append(
                                    TextPart(content="\n\n".join(text_buffer))
                                )
                                text_buffer = []
                            merged_parts.append(part)

                    # Flush any remaining text
                    if text_buffer:
                        merged_parts.append(TextPart(content="\n\n".join(text_buffer)))

                    # Render merged parts
                    for part in merged_parts:
                        self.part_renderer.render_part(part, dark_mode=self.dark_mode)
            case pd.DataFrame():
                self.part_renderer.render_dataframe(response)
            case go.Figure():
                self.part_renderer.render_plotly(response, dark_mode=self.dark_mode)
            case _:
                # Assume it's text/string-like
                self.part_renderer.render_text(str(response))


def _highlight_code(code: str, dark_mode: bool, filename: str | None = None) -> str:
    """Syntax highlight code using Pygments.

    Args:
        code: The code to highlight
        dark_mode: Whether to use dark mode styling
        filename: Optional filename to auto-detect language (e.g., "foo.py")

    Returns:
        HTML string with highlighted code, or escaped plain text if Pygments unavailable
    """
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import PythonLexer, TextLexer, get_lexer_for_filename

        if filename:
            try:
                lexer = get_lexer_for_filename(filename)
            except Exception:
                lexer = TextLexer()
        else:
            lexer = PythonLexer()

        style = "solarized-dark" if dark_mode else "solarized-light"
        formatter = HtmlFormatter(
            style=style,
            noclasses=True,
            nobackground=True,
            nowrap=True,
        )
        # Pygments adds trailing newline, strip it
        return highlight(code, lexer, formatter).rstrip('\n')
    except ImportError:
        return html_escape.escape(code)


def _highlight_shell(code: str, dark_mode: bool) -> str:
    """Custom shell command highlighting.

    Pygments' BashLexer doesn't highlight external commands (rm, tar, ls, etc.)
    or their flags. This function provides better highlighting for simple
    terminal commands by coloring:
    - Commands (first word of each line/after pipe) - blue, bold
    - Flags (words starting with -) - green
    - Pipes and operators - green, bold
    - Comments - gray, italic
    - Quoted strings - cyan

    Args:
        code: Shell commands to highlight
        dark_mode: Whether to use dark mode colors

    Returns:
        HTML string with highlighted shell commands
    """
    import re

    # Colors (solarized-inspired)
    if dark_mode:
        cmd_color = "#268BD2"  # blue - command name
        flag_color = "#859900"  # green - flags
        string_color = "#2AA198"  # cyan - quoted strings
        comment_color = "#586E75"  # gray - comments
    else:
        cmd_color = "#268BD2"
        flag_color = "#859900"
        string_color = "#2AA198"
        comment_color = "#93A1A1"

    lines = code.split("\n")
    result_lines = []

    for line in lines:
        if not line.strip():
            result_lines.append(line)
            continue

        # Handle comments
        if line.strip().startswith("#"):
            escaped = html_escape.escape(line)
            result_lines.append(
                f'<span style="color: {comment_color}; font-style: italic;">{escaped}</span>'
            )
            continue

        # Tokenize preserving whitespace
        tokens = re.split(r"(\s+)", line)
        result_tokens = []
        is_first_word = True

        for token in tokens:
            if not token:
                continue
            if token.isspace():
                result_tokens.append(token)
                continue

            escaped = html_escape.escape(token)

            # First non-whitespace token is the command
            if is_first_word:
                result_tokens.append(
                    f'<span style="color: {cmd_color}; font-weight: 600;">{escaped}</span>'
                )
                is_first_word = False
            # Flags (start with -)
            elif token.startswith("-"):
                result_tokens.append(f'<span style="color: {flag_color};">{escaped}</span>')
            # Quoted strings
            elif token.startswith(('"', "'")) or token.endswith(('"', "'")):
                result_tokens.append(
                    f'<span style="color: {string_color};">{escaped}</span>'
                )
            # Pipe, redirect, logic operators
            elif token in ("|", ">", ">>", "<", "&&", "||", ";"):
                result_tokens.append(
                    f'<span style="color: {flag_color}; font-weight: 600;">{escaped}</span>'
                )
                is_first_word = True  # Next token after pipe is also a command
            else:
                result_tokens.append(escaped)

        result_lines.append("".join(result_tokens))

    return "\n".join(result_lines)


def _render_inline_diff(old_line: str, new_line: str, dark_mode: bool, filename: str | None = None) -> tuple[str, str]:
    """Render character-level diff highlighting for a pair of changed lines.

    Returns (old_html, new_html) with specific changes highlighted and syntax colored.
    """
    try:
        from diff_match_patch import diff_match_patch
        dmp = diff_match_patch()
        diffs = dmp.diff_main(old_line, new_line)
        dmp.diff_cleanupSemantic(diffs)

        old_parts = []
        new_parts = []

        for op, text in diffs:
            highlighted = _highlight_code(text, dark_mode, filename)
            if op == 0:  # Equal
                old_parts.append(highlighted)
                new_parts.append(highlighted)
            elif op == -1:  # Delete
                old_parts.append(
                    f'<span style="background-color: var(--diff-removed-highlight);">{highlighted}</span>'
                )
            elif op == 1:  # Insert
                new_parts.append(
                    f'<span style="background-color: var(--diff-added-highlight);">{highlighted}</span>'
                )

        return "".join(old_parts), "".join(new_parts)
    except ImportError:
        return _highlight_code(old_line, dark_mode, filename), _highlight_code(new_line, dark_mode, filename)


def _render_diff_view(
    search: str, content: str, dark_mode: bool, filename: str | None = None,
    operation: str = "replace"
) -> str:
    """Render a unified diff view with line-level and character-level highlighting.

    Shows removed lines with red background, added lines with green background.
    For modified lines, highlights the specific changed characters.

    Args:
        search: The original text
        content: The replacement/insertion content
        dark_mode: Whether to use dark mode styling
        filename: Optional filename for syntax highlighting
        operation: Operation mode - "replace", "insert-after", or "insert-before"

    Returns:
        HTML string with diff-style rendering
    """
    import difflib

    # Handle insert modes - show context + inserted lines only
    if operation == "insert-after":
        # Search text kept as context, content inserted after
        html_lines = []
        for line in search.splitlines():
            highlighted = _highlight_code(line, dark_mode, filename)
            html_lines.append(f'<div style="padding-left: 20px;">{highlighted}</div>')
        for line in content.splitlines():
            highlighted = _highlight_code(line, dark_mode, filename)
            html_lines.append(
                f'<div style="background-color: var(--diff-added-bg); padding-left: 20px;">'
                f'<span style="color: var(--accent-success); user-select: none; margin-left: -16px; margin-right: 8px;">+</span>{highlighted}</div>'
            )
        inner_html = "".join(html_lines)
        return f'<div style="display: inline-block; min-width: 100%;">{inner_html}</div>'

    if operation == "insert-before":
        # Content inserted before, search text kept as context
        html_lines = []
        for line in content.splitlines():
            highlighted = _highlight_code(line, dark_mode, filename)
            html_lines.append(
                f'<div style="background-color: var(--diff-added-bg); padding-left: 20px;">'
                f'<span style="color: var(--accent-success); user-select: none; margin-left: -16px; margin-right: 8px;">+</span>{highlighted}</div>'
            )
        for line in search.splitlines():
            highlighted = _highlight_code(line, dark_mode, filename)
            html_lines.append(f'<div style="padding-left: 20px;">{highlighted}</div>')
        inner_html = "".join(html_lines)
        return f'<div style="display: inline-block; min-width: 100%;">{inner_html}</div>'

    # If identical, just show the content
    if search == content:
        highlighted = _highlight_code(search, dark_mode, filename)
        return highlighted

    old_lines = search.splitlines(keepends=True)
    new_lines = content.splitlines(keepends=True)

    # Get line-level diff operations
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    html_lines = []

    for op, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if op == 'equal':
            # Unchanged lines - no background, with syntax highlighting
            for line in old_lines[old_start:old_end]:
                highlighted = _highlight_code(line.rstrip('\n\r'), dark_mode, filename)
                html_lines.append(
                    f'<div style="padding-left: 20px;">{highlighted}</div>'
                )

        elif op == 'replace':
            # Modified lines - show old (red) then new (green) with char-level diff
            old_chunk = old_lines[old_start:old_end]
            new_chunk = new_lines[new_start:new_end]

            # Pair up lines for character-level diff where possible
            max_len = max(len(old_chunk), len(new_chunk))
            for i in range(max_len):
                if i < len(old_chunk) and i < len(new_chunk):
                    # Both exist - do character-level diff
                    old_html, new_html = _render_inline_diff(
                        old_chunk[i].rstrip('\n\r'),
                        new_chunk[i].rstrip('\n\r'),
                        dark_mode, filename
                    )
                    html_lines.append(
                        f'<div style="background-color: var(--diff-removed-bg); padding-left: 20px;">'
                        f'<span style="color: var(--accent-error); user-select: none; margin-left: -16px; margin-right: 8px;">−</span>{old_html}</div>'
                    )
                    html_lines.append(
                        f'<div style="background-color: var(--diff-added-bg); padding-left: 20px;">'
                        f'<span style="color: var(--accent-success); user-select: none; margin-left: -16px; margin-right: 8px;">+</span>{new_html}</div>'
                    )
                elif i < len(old_chunk):
                    # Only old line exists - pure deletion
                    highlighted = _highlight_code(old_chunk[i].rstrip('\n\r'), dark_mode, filename)
                    html_lines.append(
                        f'<div style="background-color: var(--diff-removed-bg); padding-left: 20px;">'
                        f'<span style="color: var(--accent-error); user-select: none; margin-left: -16px; margin-right: 8px;">−</span>{highlighted}</div>'
                    )
                else:
                    # Only new line exists - pure addition
                    highlighted = _highlight_code(new_chunk[i].rstrip('\n\r'), dark_mode, filename)
                    html_lines.append(
                        f'<div style="background-color: var(--diff-added-bg); padding-left: 20px;">'
                        f'<span style="color: var(--accent-success); user-select: none; margin-left: -16px; margin-right: 8px;">+</span>{highlighted}</div>'
                    )

        elif op == 'delete':
            # Pure deletions - red background
            for line in old_lines[old_start:old_end]:
                highlighted = _highlight_code(line.rstrip('\n\r'), dark_mode, filename)
                html_lines.append(
                    f'<div style="background-color: var(--diff-removed-bg); padding-left: 20px;">'
                    f'<span style="color: var(--accent-error); user-select: none; margin-left: -16px; margin-right: 8px;">−</span>{highlighted}</div>'
                )

        elif op == 'insert':
            # Pure insertions - green background
            for line in new_lines[new_start:new_end]:
                highlighted = _highlight_code(line.rstrip('\n\r'), dark_mode, filename)
                html_lines.append(
                    f'<div style="background-color: var(--diff-added-bg); padding-left: 20px;">'
                    f'<span style="color: var(--accent-success); user-select: none; margin-left: -16px; margin-right: 8px;">+</span>{highlighted}</div>'
                )

    # Wrap in inline-block container so backgrounds extend full width when scrolling
    inner_html = "".join(html_lines)
    return f'<div style="display: inline-block; min-width: 100%;">{inner_html}</div>'


class EventRenderer:
    """Renders agex events to themed NiceGUI components.

    Handles ActionEvent rendering with themed styling.
    """

    def __init__(self, dark_mode: bool = False):
        self.dark_mode = dark_mode

    def render_action_event(
        self,
        agent_name: str,
        full_namespace: str,
        timestamp: datetime | None,
        title: str,
        thinking: str,
        code: str,
        terminal: str = "",
        dark_mode: bool = False,
        file_actions: list[FileAction | EditAction] | None = None,
    ) -> str:
        """Generate HTML for an ActionEvent card.

        Returns HTML string for use with ui.html().
        """
        file_actions = file_actions or []
        # Separate file writes from edits
        write_actions = [a for a in file_actions if isinstance(a, FileAction)]
        edit_actions = [a for a in file_actions if isinstance(a, EditAction)]
        formatted_timestamp = (
            timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if timestamp
            else ""
        )

        # Escape content
        escaped_title = html_escape.escape(title) if title else "(processing...)"
        escaped_namespace = html_escape.escape(full_namespace or agent_name)

        thinking_section = ""
        if thinking:
            # Render thinking as markdown with relaxed list rules
            import markdown

            thinking_html = markdown.markdown(
                thinking, extensions=["fenced_code", "tables", "nl2br", "sane_lists"]
            )
            thinking_section = f"""
            <div class="themed-thinking">
                <div style="margin-top: 4px;">{thinking_html}</div>
            </div>
            """

        # File write actions section (after thinking)
        file_section = ""
        if write_actions:
            try:
                from pygments import highlight
                from pygments.formatters import HtmlFormatter
                from pygments.lexers import guess_lexer_for_filename, TextLexer

                style = "solarized-dark" if dark_mode else "solarized-light"
                formatter = HtmlFormatter(
                    style=style,
                    noclasses=True,
                    nobackground=True,
                    cssclass="highlighted-code",
                )

                file_blocks = []
                for file_action in write_actions:
                    icon = "📝" if file_action.mode == "write" else "➕"
                    mode_text = file_action.mode
                    escaped_path = html_escape.escape(file_action.path)

                    # File header bar (styled like Execution Code bar)
                    file_header = f'<div style="margin-top: 12px; margin-bottom: 8px; padding: 4px 8px; background-color: var(--bg-code); border-left: 3px solid var(--accent-secondary); font-size: 12px; font-weight: 600; color: var(--text-secondary);">{icon} {escaped_path} <span style="font-weight: 400;">({mode_text})</span></div>'

                    # Try to get appropriate lexer for file type
                    try:
                        lexer = guess_lexer_for_filename(file_action.path, file_action.content)
                    except Exception:
                        lexer = TextLexer()

                    # Syntax highlight the content with word-wrap
                    highlighted_content = highlight(file_action.content, lexer, formatter)

                    file_blocks.append(f"""
                    <div style="max-width: 100%; min-width: 0; overflow: hidden;">
                        {file_header}
                        <div style="overflow-x: auto; max-width: 100%;">{highlighted_content}</div>
                    </div>
                    """)

                file_section = f"""
                <div class="themed-files" style="margin-top: 8px; max-width: 100%; min-width: 0; overflow: hidden;">
                    {''.join(file_blocks)}
                </div>
                """
            except ImportError:
                # Fallback if Pygments isn't available
                file_badges = []
                for file_action in write_actions:
                    icon = "📝" if file_action.mode == "write" else "➕"
                    mode_text = file_action.mode
                    escaped_path = html_escape.escape(file_action.path)
                    escaped_content = html_escape.escape(file_action.content)

                    file_badges.append(f"""
                    <div style="max-width: 100%; min-width: 0; overflow: hidden;">
                        <div style="margin-top: 12px; margin-bottom: 8px; padding: 4px 8px; background-color: var(--bg-code); border-left: 3px solid var(--accent-secondary); font-size: 12px; font-weight: 600; color: var(--text-secondary);">{icon} {escaped_path} <span style="font-weight: 400;">({mode_text})</span></div>
                        <pre class="themed-code" style="margin-top: 0; overflow-x: auto; max-width: 100%;"><code>{escaped_content}</code></pre>
                    </div>
                    """)

                file_section = f"""
                <div class="themed-files" style="margin-top: 8px; max-width: 100%; min-width: 0; overflow: hidden;">
                    {''.join(file_badges)}
                </div>
                """

        # Edit actions section (search/replace edits as diff view)
        edit_section = ""
        if edit_actions:
            edit_blocks = []
            for edit_action in edit_actions:
                escaped_path = html_escape.escape(edit_action.path)

                # Build mode descriptor
                operation = getattr(edit_action, 'operation', 'replace')
                mode_parts = []
                if operation == "insert-after":
                    mode_parts.append("insert after")
                elif operation == "insert-before":
                    mode_parts.append("insert before")
                else:
                    mode_parts.append("edit")
                if edit_action.match_all:
                    mode_parts.append("all")
                mode_text = " ".join(mode_parts)

                # Render as unified diff
                diff_html = _render_diff_view(
                    edit_action.search,
                    edit_action.content,
                    dark_mode,
                    edit_action.path,
                    operation=operation,
                )

                # Edit header bar
                edit_header = f'<div style="margin-top: 12px; margin-bottom: 8px; padding: 4px 8px; background-color: var(--bg-code); border-left: 3px solid var(--accent-warning); font-size: 12px; font-weight: 600; color: var(--text-secondary);">✏️ {escaped_path} <span style="font-weight: 400;">({mode_text})</span></div>'

                edit_blocks.append(f"""
                <div style="max-width: 100%; min-width: 0; overflow: hidden;">
                    {edit_header}
                    <pre class="themed-code" style="margin: 0; padding: 8px; background: transparent; border-radius: 4px; overflow-x: auto; font-size: 13px; line-height: 1.4;"><code>{diff_html}</code></pre>
                </div>
                """)

            edit_section = f"""
            <div class="themed-edits" style="margin-top: 8px; max-width: 100%; min-width: 0; overflow: hidden;">
                {''.join(edit_blocks)}
            </div>
            """

        # Code section with delimiter if files were generated
        code_section = ""
        code_delimiter = ""
        if (write_actions or edit_actions) and code:
            code_delimiter = '<div style="margin-top: 16px; margin-bottom: 8px; padding: 4px 8px; background-color: var(--bg-code); border-left: 3px solid var(--accent-primary); font-size: 12px; font-weight: 600; color: var(--text-secondary);">⚙️ Execution Code</div>'

        if code:
            highlighted = _highlight_code(code, dark_mode)  # Python by default
            code_section = f"""
            {code_delimiter}
            <div style="margin-top: 4px;">
                <div style="overflow-x: auto;"><pre class="themed-code" style="margin: 0;"><code>{highlighted}</code></pre></div>
            </div>
            """

        # Terminal section (shell commands) with green accent
        terminal_section = ""
        terminal_delimiter = ""
        if (write_actions or edit_actions) and terminal:
            terminal_delimiter = '<div style="margin-top: 16px; margin-bottom: 8px; padding: 4px 8px; background-color: var(--bg-code); border-left: 3px solid var(--accent-success); font-size: 12px; font-weight: 600; color: var(--text-secondary);">💻 Terminal</div>'

        if terminal:
            highlighted_terminal = _highlight_shell(terminal, dark_mode)
            terminal_section = f"""
            {terminal_delimiter}
            <div style="margin-top: 4px;">
                <div style="overflow-x: auto;"><pre class="themed-code" style="margin: 0;"><code>{highlighted_terminal}</code></pre></div>
            </div>
            """

        return f"""
        <div class="themed-event-card">
            <div class="themed-event-header">
                {escaped_title}
            </div>
            {thinking_section}
            {file_section}
            {edit_section}
            {code_section}
            {terminal_section}
        </div>
        """

    def render_file_event(self, event: "FileEvent") -> str:
        """Render a file event as a markdown string.

        Args:
            event: The FileEvent to render
        
        Returns:
            Markdown string describing the file changes
        """
        parts = []
        action = "Uploaded" if event.file_source == "user" else "Changes"
        
        items = []
        if event.added:
            prefix = "Added"
            items = event.added
        if event.modified:
            prefix = "Modified"
            items = event.modified
        if event.removed:
            prefix = "Removed"
            items = event.removed
        
        items = sorted(f"`{item}`" for item in items)
        parts.append(f"**{prefix}:** {', '.join(items)}")
        
        return "\n\n".join(parts)

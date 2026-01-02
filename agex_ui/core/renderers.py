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
        dark_mode: bool = False,
    ) -> str:
        """Generate HTML for an ActionEvent card.

        Returns HTML string for use with ui.html().
        """
        formatted_timestamp = (
            timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if timestamp
            else ""
        )

        # Escape content
        escaped_title = html_escape.escape(title) if title else "(processing...)"
        escaped_code = html_escape.escape(code) if code else ""
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

        code_section = ""
        if escaped_code:
            # Use Pygments for syntax highlighting
            try:
                from pygments import highlight
                from pygments.formatters import HtmlFormatter
                from pygments.lexers import PythonLexer

                # Use theme-appropriate style
                style = "solarized-dark" if dark_mode else "solarized-light"
                formatter = HtmlFormatter(
                    style=style,
                    noclasses=True,
                    nobackground=True,  # Transparent background
                    cssclass="highlighted-code",
                )

                # Highlight the code (use unescaped code for Pygments)
                highlighted = highlight(code, PythonLexer(), formatter)

                code_section = f"""
                <div style="margin-top: 12px;">
                    <div style="margin-top: 4px; overflow-x: auto;">{highlighted}</div>
                </div>
                """
            except ImportError:
                # Fallback if Pygments isn't available
                code_section = f"""
                <div style="margin-top: 8px;">
                    <pre class="themed-code" style="margin-top: 4px; margin-bottom: 0;"><code>{escaped_code}</code></pre>
                </div>
                """

        return f"""
        <div class="themed-event-card">
            <div class="themed-event-header">
                {escaped_title}
            </div>
            {thinking_section}
            {code_section}
        </div>
        """

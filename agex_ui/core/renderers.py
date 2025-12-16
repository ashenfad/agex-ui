"""UI renderers for responses and events.

This module handles converting agent responses and events into NiceGUI components.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from agex import OutputEvent
from agex.eval.objects import ImageAction
from nicegui import ui

from agex_ui.core.responses import (
    DataFramePart,
    PlotlyPart,
    Response,
    ResponsePart,
    TextPart,
)


class ResponseRenderer:
    """Renders response parts to NiceGUI components."""

    def render_text(self, text: str, container: ui.element | None = None):
        """Render markdown text.
        
        Args:
            text: Markdown text to render
            container: Optional container element (uses current context if None)
        """
        markdown = ui.markdown(
            text, extras=["fenced-code-blocks", "tables", "cuddled-lists"]
        )
        if container is not None:
            with container:
                markdown

    def render_dataframe(
        self, df: pd.DataFrame, container: ui.element | None = None
    ):
        """Render pandas DataFrame as table.
        
        Args:
            df: DataFrame to render
            container: Optional container element (uses current context if None)
        """
        table = ui.table.from_pandas(df).classes("w-full")
        if container is not None:
            with container:
                table

    def render_plotly(
        self, fig: go.Figure, container: ui.element | None = None
    ):
        """Render Plotly figure.
        
        Args:
            fig: Plotly figure to render
            container: Optional container element (uses current context if None)
        """
        plot = ui.plotly(fig).classes("w-full h-96").style(
            "width: 640px; min-height: 400px"
        )
        if container is not None:
            with container:
                plot

    def render_part(self, part: ResponsePart):
        """Render a single response part based on its type."""
        match part:
            case TextPart(content=text):
                self.render_text(text)
            case DataFramePart(df=df):
                self.render_dataframe(df)
            case PlotlyPart(figure=fig):
                self.render_plotly(fig)
            case _:
                # Fallback: render as text
                self.render_text(str(part))

    def render_response(self, response: str | pd.DataFrame | go.Figure | Response):
        """Render a complete response (handles mixed types).
        
        Args:
            response: Can be a single type (str, DataFrame, Figure) or a Response object
        """
        match response:
            case Response():
                # Render each part of a multi-part response
                for part in response.normalize():
                    self.render_part(part)
            case pd.DataFrame():
                self.render_dataframe(response)
            case go.Figure():
                self.render_plotly(response)
            case _:
                # Assume it's text/string-like
                self.render_text(str(response))


class EventRenderer:
    """Renders agex events to HTML/UI components."""

    def extract_plotly_figures(
        self, evt: OutputEvent
    ) -> tuple[list[go.Figure], list[Any]]:
        """Separate Plotly figures from other OutputEvent parts.
        
        Args:
            evt: OutputEvent to process
            
        Returns:
            (plotly_figures, other_parts) where plotly_figures is a list of 
            go.Figure objects and other_parts contains everything else
        """
        plotly_figures = []
        other_parts = []

        for part in evt.parts:
            if isinstance(part, ImageAction):
                # Check if the image is a Plotly figure
                if hasattr(part.image, "to_image") and callable(
                    getattr(part.image, "to_image", None)
                ):
                    plotly_figures.append(part.image)
                else:
                    other_parts.append(part)
            else:
                other_parts.append(part)

        return plotly_figures, other_parts

    def render_output_event_with_plotly(
        self, evt: OutputEvent, plotly_figures: list[go.Figure]
    ):
        """Render an OutputEvent card with embedded Plotly figures.
        
        Args:
            evt: The OutputEvent to render
            plotly_figures: List of Plotly figures to embed in the card
        """
        import html as html_escape

        formatted_timestamp = (
            evt.timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if evt.timestamp
            else ""
        )
        metadata_line = formatted_timestamp
        if evt.commit_hash:
            metadata_line += f' • <code style="background: #f1f3f4; padding: 1px 4px; border-radius: 2px; font-family: monospace; font-size: 11px;">{evt.commit_hash[:8]}</code>'

        # Create card container matching OutputEvent.as_html() structure
        with (
            ui.card()
            .classes("w-full")
            .style(
                "border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; margin: 8px 0; background: #f6f8fa;"
            )
        ):
            # Header matching OutputEvent structure
            ui.html(
                f"""
                <div style="font-weight: 600; color: #24292e; margin-bottom: 8px; font-size: 14px;">
                    🤖 OutputEvent - {html_escape.escape(evt.full_namespace or evt.agent_name)}
                </div>
                <div style="font-size: 12px; color: #6a737d; margin-bottom: 12px;">
                    {metadata_line}
                </div>
                <div style="border-left: 3px solid #6f42c1; padding-left: 10px; margin: 5px 0;">
                    <h4 style="margin: 0 0 5px 0; font-size: 1em; color: #6f42c1;">📤 Output:</h4>
                </div>
                """,
                sanitize=False,
            ).classes("w-full p-0 my-0")

            # Render each Plotly figure
            for fig in plotly_figures:
                # Update figure layout to be responsive
                if hasattr(fig, "update_layout"):
                    fig.update_layout(
                        autosize=True,
                        width=None,
                        height=None,
                    )
                ui.plotly(fig).classes("w-full h-96").style(
                    "width: 640px; min-height: 400px"
                )

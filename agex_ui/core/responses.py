"""Response type definitions for agent outputs.

This module defines the types that agents can return in their responses,
including text, dataframes, and plotly figures. Users can extend these
with custom response types.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.graph_objects as go


@dataclass
class ResponsePart:
    """Base class for all response parts."""

    pass


@dataclass
class TextPart(ResponsePart):
    """Text/markdown content."""

    content: str


@dataclass
class DataFramePart(ResponsePart):
    """Pandas DataFrame table."""

    df: pd.DataFrame


@dataclass
class PlotlyPart(ResponsePart):
    """Plotly figure visualization."""

    figure: go.Figure


@dataclass
class Response:
    """Multi-part response container.

    Supports a flexible list of parts that can be:
    - Raw types: str, pd.DataFrame, go.Figure
    - ResponsePart subclasses: TextPart, DataFramePart, PlotlyPart

    Example:
        >>> Response(parts=["Analysis complete", df, plotly_fig])
        >>> Response(parts=[TextPart("Status: OK"), DataFramePart(df)])
    """

    parts: list[ResponsePart | str | pd.DataFrame | go.Figure]

    def normalize(self) -> list[ResponsePart]:
        """Convert all parts to ResponsePart instances.

        Raw types are automatically wrapped:
        - str → TextPart
        - pd.DataFrame → DataFramePart
        - go.Figure → PlotlyPart
        """
        normalized = []
        for part in self.parts:
            if isinstance(part, ResponsePart):
                normalized.append(part)
            elif isinstance(part, str):
                normalized.append(TextPart(content=part))
            elif isinstance(part, pd.DataFrame):
                normalized.append(DataFramePart(df=part))
            elif isinstance(part, go.Figure):
                normalized.append(PlotlyPart(figure=part))
            else:
                # For unknown types, try converting to string
                normalized.append(TextPart(content=str(part)))
        return normalized

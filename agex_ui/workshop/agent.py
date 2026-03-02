"""Workshop agent configured for building NiceGUI apps."""
import calgebra
import calgebra.gcsa as gcsa
import calgebra.mutable as mutable
from agex import Agent, connect_fs, connect_llm, connect_state
from agex.helpers import register_pandas, register_plotly, register_stdlib
from calgebra import to_dataframe, ICalEvent

from agex_ui.core.responses import Response
from agex_ui.workshop.primer import PRIMER

USER_CONTEXT = "## User Context\n\n- Default timezone: America/Los_Angeles"
PRIMER_PARTS = [
    PRIMER,
    USER_CONTEXT,
    calgebra.docs.api,
    calgebra.docs.quick_start,
    calgebra.docs.tutorial,
]

agent = Agent(
    name="Workshop",
    primer="\n\n".join(PRIMER_PARTS),
    llm=connect_llm(
        provider="gemini",
        model="gemini-3-flash-preview",
    ),
    state=connect_state(
        type="versioned",
        storage="disk",
        path="/tmp/agex/workshop",
    ),
    fs=connect_fs(type="virtual"),
)

# Register calgebra
agent.module(calgebra, recursive=True, visibility="low")

# Highlight key bits of calgebra
agent.cls(ICalEvent, visibility="high")
agent.cls(mutable.WriteResult, visibility="medium")
agent.fn(to_dataframe, visibility="high")

# Enable stdlib & data-oriented libs via helpers
register_stdlib(agent, io_friendly=True)
register_pandas(agent, io_friendly=True)
register_plotly(agent, io_friendly=True)

# Register Response type from core
agent.cls(Response)


@agent.task
async def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, analyze the calendars and return a multi-part response.
    - str: Conversational responses rendered as Markdown
    - DataFrame: Tables for displaying events, calendars, or options
    - Figure: Plotly charts for visualizations

    If the user asks for a NiceGUI app, help them build it by writing to app/main.py
    """
    pass

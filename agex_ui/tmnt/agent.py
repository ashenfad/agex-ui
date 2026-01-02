"""TMNT Calendar Agent.

A demo calendar assistant that uses local iCal files for the four turtles.
"""

import calgebra
import calgebra.mutable as mutable
from agex import Agent, connect_llm, connect_state
from agex.helpers import register_pandas, register_plotly, register_stdlib, register_numpy
from calgebra import to_dataframe, ICalEvent

from agex_ui.tmnt.primer import PRIMER
from agex_ui.tmnt.utils import TZ, load_cals
from agex_ui.core.responses import Response

USER_CONTEXT = f"## User Context\n\n- Default timezone: {TZ}"
PRIMER_PARTS = [
    PRIMER,
    USER_CONTEXT,
    calgebra.docs.api,
    calgebra.docs.quick_start,
]

agent = Agent(
    name="TMNT Helper",
    primer="\n\n".join(PRIMER_PARTS),
    llm=connect_llm(provider="gemini", model="gemini-3-flash-preview"),
    state=connect_state(
        type="versioned",
        storage="disk",
        path="/tmp/agex/tmnt",
        init=load_cals(),  # Initialize state with calendars
    ),
)

# Register calgebra
agent.module(calgebra, recursive=True, visibility="low")

# Highlight key bits of calgebra
agent.cls(ICalEvent, visibility="high")
agent.cls(mutable.WriteResult, visibility="medium")
agent.fn(to_dataframe, visibility="high")

# Enable stdlib & data-oriented libs via helpers
register_stdlib(agent)
register_pandas(agent)
register_plotly(agent)

# Register Response type from core
agent.cls(Response)

# The setup runs before a task to help provide programmatic context to the agent
SETUP_ACTION = """
from datetime import date
from calgebra import at_tz
today = date.today().isoformat()
at = at_tz("America/Los_Angeles")
task_continue(f"Current date: {today}. 'at' is ready in your env.")
"""

@agent.task(setup=SETUP_ACTION)
async def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, analyze the turtle calendars and return a multi-part response.
    - str: Conversational responses rendered as Markdown
    - DataFrame: Tables for displaying events, calendars, or options
    - Figure: Plotly charts for visualizations
    """
    pass

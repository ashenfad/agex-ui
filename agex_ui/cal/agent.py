import calgebra
import calgebra.gcsa as gcsa
import calgebra.mutable as mutable
from agex import Agent, connect_llm, connect_state, connect_fs
from agex.helpers import register_pandas, register_plotly, register_stdlib
from calgebra import to_dataframe
from calgebra.gcsa import Event

from agex_ui.cal.primer import PRIMER
from agex_ui.cal.utils import user_timezone
from agex_ui.core.responses import Response

TZ = user_timezone()
USER_CONTEXT = f"## User Context\n\n- Default timezone: {TZ}"
PRIMER_PARTS = [
    PRIMER,
    USER_CONTEXT,
    calgebra.docs.api,
    calgebra.docs.quick_start,
    calgebra.docs.gcsa,
]

agent = Agent(
    name="Cal",
    primer="\n\n".join(PRIMER_PARTS),
    llm=connect_llm(
        provider="gemini",
        model="gemini-3-flash-preview",
        google_search=True,
        url_context=True,
    ),
    state=connect_state(
        type="versioned",
        storage="disk",
        path="/tmp/agex/cal",
    ),
    fs=connect_fs(type="virtual"),
    max_iterations=10,
    eval_timeout_seconds=15,
    log_high_water_tokens=100000,
)

# Register calgebra w/ host fs access (for indirect google oauth)
agent.module(calgebra, recursive=True, visibility="low", host_fs_access=True)

# Highlight key bits of calgebra
agent.cls(Event, visibility="high")
agent.cls(mutable.WriteResult, visibility="medium")
agent.fn(to_dataframe, visibility="high")

# Local helper functions
agent.fn(user_timezone, visibility="high")

# Enable stdlib & data-oriented libs via helpers
register_stdlib(agent)
register_pandas(agent)
register_plotly(agent)

# Register Response type from core
agent.cls(Response)


# The setup runs before a task to help provide programmatic context to the agent
SETUP_ACTION = """
import pandas as pd
from datetime import date
from calgebra.gcsa import calendars
from calgebra import at_tz

today = date.today().isoformat()
at = at_tz("America/Los_Angeles")

cals = calendars()
cal_summaries = pd.DataFrame(
    {"calendar_summary": [c.calendar_summary for c in cals]}
)
task_continue(f"Current date: {today}. Available calendars (by index):", cal_summaries)
"""


@agent.task(setup=SETUP_ACTION)
async def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, take actions to modify the calendar if necessary.
    Then respond to the user via str, dataframe, or plotly figure.

    - str: Conversational responses rendered as Markdown
    - DataFrame: Tables for displaying events, calendars, or options
    - Figure: Plotly charts for visualizations
    """
    pass

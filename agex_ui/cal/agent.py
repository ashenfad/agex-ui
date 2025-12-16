import calgebra
import calgebra.gcsa as gcsa
import calgebra.mutable as mutable
from agex import Agent, Versioned, connect_llm
from agex.helpers import register_pandas, register_plotly, register_stdlib
from agex.state.kv import Disk
from calgebra.gcsa import Event

from agex_ui.cal.primer import PRIMER
from agex_ui.cal.utils import events_to_dataframe, intervals_to_dataframe, user_timezone
from agex_ui.core.responses import Response  # Import from core instead

USER_TIMEZONE = user_timezone()
USER_CONTEXT = f"## User Context\n\n- Default timezone: {USER_TIMEZONE}"
PRIMER_PARTS = [
    PRIMER,
    USER_CONTEXT,
    calgebra.docs["api"],
    calgebra.docs["quick_start"],
    # calgebra.docs["tutorial"],
    calgebra.docs["gcsa"],
]

agent = Agent(
    name="cal",
    primer="\n\n".join(PRIMER_PARTS),
    llm_client=connect_llm(provider="anthropic", model="claude-haiku-4-5"),
    # llm_client=connect_llm(provider="anthropic", model="claude-sonnet-4-5"),
    max_iterations=10,
    timeout_seconds=15,
    log_high_water_tokens=150000
)

# persisted state so agent can learn
state = Versioned(Disk("/tmp/agex-ui-cal"))


# Register calgebra
agent.module(calgebra, recursive=True, visibility="low")

# Highlight key calgebra gcsa and mutable modules and classes
agent.module(gcsa, visibility="low")
agent.cls(Event, visibility="high")
agent.cls(mutable.WriteResult, visibility="medium")

# Local helper functions
agent.fn(events_to_dataframe, visibility="high")
agent.fn(intervals_to_dataframe, visibility="high")
agent.fn(user_timezone, visibility="high")


# Enable stdlib & data-oriented libs via helpers
register_stdlib(agent)
register_pandas(agent)
register_plotly(agent)

# Register Response type from core
agent.cls(Response)


SETUP_ACTION = """
import pandas as pd
from datetime import date
from calgebra.gcsa import calendars

today = date.today().isoformat()

cals = calendars()
cal_summaries = pd.DataFrame(
    {"calendar_summary": [c.calendar_summary for c in cals]}
)
task_continue(f'Current date: {today}. Available calendars (by index):', cal_summaries)
"""


@agent.task(setup=SETUP_ACTION)
def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, take actions to modify the calendar if necessary.
    Then respond to the user via str, dataframe, or plotly figure.

    - str: Conversational responses rendered as Markdown
    - DataFrame: Tables for displaying events, calendars, or options
    - Figure: Plotly charts for visualizations
    """
    pass

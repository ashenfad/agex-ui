from dataclasses import dataclass

import calgebra
import gcsa
import pandas as pd
import plotly.graph_objects as go
from agex import Agent, Versioned, connect_llm
from agex.helpers import register_pandas, register_plotly, register_stdlib
from agex.state.kv import Disk

# calgebra imports for read/query operations
from calgebra.gcsa import Calendar, CalendarItem, Event, list_calendars

# gcsa imports for write operations
from gcsa.event import Event as GoogleEvent
from gcsa.google_calendar import GoogleCalendar

from agex_ui.cal import utils
from agex_ui.cal.primer import PRIMER

# persisted state so agent can learn and build helper fns
state = Versioned(store=Disk("/tmp/agex-ui-cal"))

CALGEBRA_TUTORIAL: str = calgebra.docs["tutorial"]
CALGEBRA_API_REFERENCE: str = calgebra.docs["api"]


USER_TIMEZONE = utils.user_timezone()
USER_CONTEXT = f"## User Context\n\n- Default timezone: {USER_TIMEZONE}"


EVENT_TABLE_GUIDE = """
## Event Table Helper
- Use `events_to_dataframe(events, timezone_name=None)` to convert event iterables into standardized tables.
- Columns: `calendar` (email sans `@gmail.com`), `summary`, `start` (localized string), `duration` (single-unit shorthand).
"""

FULL_PRIMER = (
    PRIMER
    + "\n\n"
    + USER_CONTEXT
    + "\n\n"
    + EVENT_TABLE_GUIDE
    + "\n\n"
    + CALGEBRA_TUTORIAL
    + "\n\n"
    + CALGEBRA_API_REFERENCE
)

agent = Agent(
    name="cal",
    primer=FULL_PRIMER,
    # llm_client=dummy_llm_client,
    llm_client=connect_llm(
        provider="openai",
        model="gpt-5-mini",
        reasoning_effort="low",  # low reasoning to keep things snappy
    ),
)

# Register calgebra for read/query operations (composable DSL)
agent.module(calgebra, recursive=True, visibility="low")

# Highlight key calgebra functions
agent.fn(list_calendars, visibility="high")
agent.cls(Event, visibility="medium")
agent.cls(Calendar, visibility="medium")
agent.cls(CalendarItem, visibility="medium")

# Highlight gcsa classes needed for mutations
agent.cls(GoogleCalendar, visibility="medium")
agent.cls(GoogleEvent, visibility="medium")

# Register gcsa for write operations (create, update, delete events)
agent.module(gcsa, recursive=True, visibility="low")
# Local helper functions
agent.module(utils, visibility="high")


# Enable stdlib & data-oriented libs via helpers
register_stdlib(agent)
register_pandas(agent)
register_plotly(agent)


@agent.cls
@dataclass
class Response:
    parts: list[str | pd.DataFrame | go.Figure]


@agent.task
def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, take actions to modify the calendar if necessary.
    Then respond to the user via str, dataframe, or plotly figure.

    - str: Conversational responses rendered as Markdown
    - DataFrame: Tables for displaying events, calendars, or options
    - Figure: Plotly charts for visualizations
    """
    pass

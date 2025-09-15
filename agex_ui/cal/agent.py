import pandas as pd
import plotly.graph_objects as go
import gcsa

from agex import Agent, Versioned, connect_llm
from agex.state.kv import Disk
from agex.helpers import register_pandas, register_stdlib, register_plotly

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from gcsa.recurrence import Recurrence
from gcsa.calendar import Calendar, CalendarListEntry
from agex_ui.cal.primer import PRIMER

state = Versioned(store=Disk("/tmp/agex-ui-cal"))
agent = Agent(
    name="cal",
    primer=PRIMER,
    llm_client=connect_llm(provider="openai", model="gpt-5", reasoning_effort="low"),
)

agent.module(gcsa, recursive=True)
agent.cls(GoogleCalendar, visibility="medium")
agent.cls(Event, visibility="medium")
agent.cls(Recurrence, visibility="medium")
agent.cls(Calendar, visibility="medium")
agent.cls(CalendarListEntry, visibility="medium")

register_pandas(agent)
register_stdlib(agent)
register_plotly(agent)


@agent.task
def handle_prompt(prompt: str) -> str | pd.DataFrame | go.Figure:
    """
    Given a user prompt, take actions to modify the calendar if necessary.
    Then respond to the user via str, dataframe, or plotly figure.

    Dataframes will be displayed as a table to the user, plotly figures
    will be displayed as a plot.
    """
    pass

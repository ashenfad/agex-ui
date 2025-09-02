from typing import Any
import nicegui
import nicegui.ui as ui
from agex import Agent, connect_llm, Live
from agex.helpers import (
    register_pandas,
    register_plotly,
    register_stdlib,
    register_numpy,
)
from agex_ui.chat.primer import PRIMER


state = Live()
agent = Agent(
    name="nicegui",
    primer=PRIMER,
    llm_client=connect_llm(provider="openai", model="gpt-5", reasoning_effort="medium"),
)


# let the agent use nicegui
agent.module(nicegui, recursive=True, visibility="low")

# agents are less familiar with nicegui v2, so we'll add
# basic constructor sigs for ui elements to the context
agent.module(ui, recursive=True, visibility="medium")

# enable stdlib & data-oriented libs via helpers
# we're trusting the agent with io (so it can use temp files)
register_stdlib(agent, io_friendly=True)
register_pandas(agent, io_friendly=True)
register_plotly(agent, io_friendly=True)
register_numpy(agent, io_friendly=True)


@agent.task
def handle_prompt(prompt: str, col: ui.column):
    """
    Given a user prompt, respond to the user by assembling a NiceGUI components.
    """
    pass


@agent.task
def handle_form_submission(bound_vars: dict[str, Any], col: ui.column):
    """
    Given form data from a user interaction, process it and build a NiceGUI response.
    bound_vars contains the values from form inputs that the agent previously created.
    """
    pass

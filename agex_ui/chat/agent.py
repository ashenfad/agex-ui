from typing import Any
import nicegui
import nicegui.ui as ui
from agex import Agent, connect_llm, Live, view, summarize_capabilities
from agex.helpers import (
    register_pandas,
    register_plotly,
    register_stdlib,
    register_numpy,
)
from agex_ui.chat.primer import PRIMER


state = Live()
agent = Agent(
    name="chat",
    primer=PRIMER,
    llm_client=connect_llm(provider="openai", model="gpt-5", reasoning_effort="medium"),
)


# enable stdlib & data-oriented libs via helpers
# we're trusting the agent with io (so it can use temp files)
register_stdlib(agent, io_friendly=True)
register_pandas(agent, io_friendly=True)
register_plotly(agent, io_friendly=True)
register_numpy(agent, io_friendly=True)

# let the agent use nicegui but agents are less familiar with v2...
# so we'll expose the ui module with high visibility
agent.module(nicegui, recursive=True, visibility="low")
agent.module(ui, recursive=True, visibility="high")

# nicegui's ui module documentation is *huge* (~385K tokens)! so we'll
# summarize it via this helper to replace the standard visibility rendering
agent.capabilities_primer = summarize_capabilities(
    agent,
    target_chars=16000,
    llm_client=connect_llm(provider="openai", model="gpt-4.1", max_tokens=8000),
    use_cache=True,  # cache to `.agex` so we only build this once
)


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

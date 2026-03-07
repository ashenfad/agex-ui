"""Marimo Assistant agent configured for notebook development."""

import marimo as mo

from agex import Agent, connect_fs, connect_llm, connect_state
from agex.helpers import register_pandas, register_plotly, register_stdlib

from agex_ui.core.responses import Response
from agex_ui.marimo_assistant.marimo_bridge import (
    get_cell_details,
    get_errors,
    get_notebook_data,
    get_variable_info,
    read_cells,
    set_variable,
    write_notebook,
)
from agex_ui.marimo_assistant.primer import PRIMER

agent = Agent(
    name="Marimo Assistant",
    primer=PRIMER,
    llm=connect_llm(
        provider="gemini",
        model="gemini-3-flash-preview",
    ),
    state=connect_state(
        type="versioned",
        storage="disk",
        path="/tmp/agex/marimo_assistant",
    ),
    fs=connect_fs(type="virtual"),
    max_iterations=15,
)

# Data science libraries for sandbox iteration
register_stdlib(agent, io_friendly=True)
register_pandas(agent, io_friendly=True)
register_plotly(agent, io_friendly=True)

# marimo for testing cell code in the sandbox
agent.module(mo, recursive=True, visibility="low")

# Bridge functions — reading notebook state
agent.fn(read_cells, visibility="high", host_fs_access=True)
agent.fn(get_cell_details, visibility="medium", host_fs_access=True)
agent.fn(get_variable_info, visibility="high", host_fs_access=True)
agent.fn(get_errors, visibility="high", host_fs_access=True)

# Bridge functions — direct kernel access
agent.fn(get_notebook_data, visibility="high", host_fs_access=True)
agent.fn(set_variable, visibility="medium", host_fs_access=True)

# Bridge functions — writing cells
agent.fn(write_notebook, visibility="high", host_fs_access=True)

# Response type
agent.cls(Response)


@agent.task
async def handle_prompt(prompt: str) -> Response:
    """
    Given a user prompt, help them build or refine their marimo notebook.

    Use read_cells() to understand the current notebook state.
    Use get_notebook_data() to get real Python objects from the live kernel.
    Use write_notebook() to deliver verified cells to the editor.

    Return a Response with a summary of what you did.
    """
    pass

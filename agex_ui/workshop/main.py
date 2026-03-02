"""Workshop: Conversational app builder interface."""

from nicegui import app, ui

from agex_ui.core.turn import TurnConfig
from agex_ui.templates.chat_interface import ChatInterfaceConfig, create_chat_interface
from agex_ui.workshop.agent import agent, handle_prompt

app.add_static_files("/assets", "./assets")

chat_config = ChatInterfaceConfig(
    title="Workshop",
    page_title="Workshop",
    greeting="Hi! I can help you build interactive apps. Describe what you'd like to create.",
    max_width="100%",
    min_width="300px",
    enable_app_preview=True,
)

turn_config = TurnConfig(
    show_setup_events=False,
    enable_token_streaming=True,
    auto_scroll=True,
    collapse_agent_activity=True,
)


@ui.page("/")
def index(branch: str | None = None):
    create_chat_interface(
        agent=agent,
        agent_task=handle_prompt,
        config=chat_config,
        turn_config=turn_config,
        initial_branch=branch,
    )


ui.run(favicon="🔧", storage_secret="agex-ui-workshop-secret")

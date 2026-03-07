"""Marimo Assistant: Chat + live marimo editor side-by-side."""

from pathlib import Path

from nicegui import app, ui

from agex_ui.core.turn import TurnConfig
from agex_ui.marimo_assistant.marimo_bridge import set_notebook_path
from agex_ui.marimo_assistant.marimo_mount import create_edit_app
from agex_ui.templates.chat_interface import ChatInterfaceConfig, create_chat_interface

# --- Notebook setup ---

NOTEBOOK_DIR = Path(__file__).parent.parent.parent / "notebooks"
NOTEBOOK_DIR.mkdir(exist_ok=True)
NOTEBOOK_PATH = NOTEBOOK_DIR / "scratch.py"

# Create starter notebook if it doesn't exist
if not NOTEBOOK_PATH.exists():
    NOTEBOOK_PATH.write_text(
        'import marimo\n\napp = marimo.App()\n\n\n@app.cell\ndef _():\n'
        '    import marimo as mo\n    mo.md("# Scratch Notebook")\n    return\n\n\n'
        'if __name__ == "__main__":\n    app.run()\n'
    )

# Configure the bridge
set_notebook_path(str(NOTEBOOK_PATH))

# --- Mount marimo editor ---

marimo_app = create_edit_app(str(NOTEBOOK_PATH))
app.mount("/notebook", marimo_app)

# --- Import agent after bridge is configured ---

from agex_ui.marimo_assistant.agent import agent, handle_prompt  # noqa: E402

# --- Static assets ---

app.add_static_files("/assets", "./assets")


# --- Custom right panel: marimo iframe ---

def marimo_panel():
    """Build the marimo editor iframe for the right side of the splitter."""
    ui.html(
        '<iframe src="/notebook/" '
        'style="width: 100%; height: 100%; border: none;">'
        "</iframe>",
        sanitize=False,
    ).style("width: 100%; height: 100%;")


# --- Config ---

chat_config = ChatInterfaceConfig(
    title="Marimo Assistant",
    page_title="Marimo Assistant",
    greeting=(
        "Hi! I can help you build a marimo notebook. "
        "Describe what you'd like to create, or ask me to inspect the current notebook."
    ),
    max_width="100%",
    min_width="300px",
    custom_right_panel=marimo_panel,
)

turn_config = TurnConfig(
    show_setup_events=False,
    enable_token_streaming=True,
    auto_scroll=True,
    collapse_agent_activity=True,
)


@ui.page("/")
def index():
    create_chat_interface(
        agent=agent,
        agent_task=handle_prompt,
        config=chat_config,
        turn_config=turn_config,
    )


ui.run(
    favicon="📓",
    storage_secret="agex-ui-marimo-assistant-secret",
    reload=False,  # Disable auto-reload — marimo saves .py files which would trigger restart
)

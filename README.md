# agex-ui

A demo for building agent-driven user interfaces with [`agex`](https://ashenfad.github.io/agex/) and [NiceGUI](https://nicegui.io/).

**agex-ui** provides components for creating chat interfaces where AI agents can respond with text, dataframes, and plotly visualizations, with real-time streaming of agent activity.

## Features

This repository serves as a reference implementation for integrating `agex` agents into a web UI.

- **Multi-Type Responses**: Renders text, DataFrames, and Plotly figures.
- **Real-Time Streaming**: Displays agent thought and action events as they happen.
- **Agent Integration**: Standard patterns for connecting `agex` tasks to the UI.
- **State Persistence**: Support for restoring chat from state and reverting agent actions.

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/ashenfad/agex-ui.git
cd agex-ui
pip install -e .
```

### Running the TMNT Demo

The TMNT (Turtle Scheduling) demo works out of the box with local iCal files—no OAuth required:

```bash
python -m agex_ui.tmnt.main
```

Then open your browser to the displayed URL (typically `http://localhost:8080`).

> [!NOTE]
> **LLM Configuration Required**: Set your [LLM provider credentials](https://ashenfad.github.io/agex/api/llm/) (e.g., `GOOGLE_API_KEY` for Gemini).

This demo showcases a calendar assistant that helps schedule the four half-shelled heroes using the [`calgebra`](https://github.com/ashenfad/calgebra) library.

## Architecture

```
agex_ui/
├── core/           # Reusable framework components
│   ├── responses.py    # Response type system (Response, ResponsePart, etc.)
│   ├── renderers.py    # UI renderers for responses and events
│   ├── events.py       # Event handling and token streaming
│   ├── turn.py         # Turn orchestration (run_agent_turn)
│   ├── history.py      # Chat history restoration from state
│   ├── theme.py        # Theme management with CSS variables
│   └── utils.py        # Shared UI utilities
├── templates/      # UI templates
│   └── chat_interface.py  # Standard chat interface template
├── tmnt/           # TMNT demo (local iCal files, no OAuth)
│   ├── agent.py        # Agent definition with calgebra integration
│   ├── main.py         # Application entry point
│   ├── primer.py       # Agent system prompts
│   └── utils.py        # Calendar loading utilities
└── cal/            # Google Calendar example (requires OAuth)
    ├── agent.py        # Agent with Google Calendar integration
    ├── main.py         # Application entry point
    ├── primer.py       # Agent system prompts
    └── utils.py        # Calendar-specific utilities
```

## Building Your Own Agent-Driven UI

Here's how to create a custom agent-driven chat interface:

### 1. Define Your Agent Task

```python
# my_agent.py
from agex import Agent, connect_llm
from agex_ui.core.responses import Response
import pandas as pd

agent = Agent(
    name="my_agent",
    primer="You are a helpful assistant...",
    llm=connect_llm(provider="anthropic", model="claude-haiku-4-5"),
)

# Register the Response type
agent.cls(Response)

@agent.task
def handle_prompt(prompt: str) -> Response:
    """Process user prompt and return a multi-part response."""
    # Your agent logic here
    return Response(parts=[
        "Here's your analysis:",
        pd.DataFrame({"col1": [1, 2, 3]}),
    ])
```

### 2. Create the Chat Interface

```python
# main.py
from nicegui import ui, app
from agex_ui.templates import create_chat_interface, ChatInterfaceConfig
from agex_ui.core.turn import TurnConfig
from my_agent import agent, handle_prompt

app.add_static_files("/assets", "./assets")

@ui.page("/")
def index():
    # Create interface (returns chat_messages, chat_input, theme_manager)
    chat_messages, chat_input, theme = create_chat_interface(
        agent=agent,
        agent_task=handle_prompt,
        config=ChatInterfaceConfig(
            title="My Agent App",
            page_title="My App",
            greeting="Hello! How can I help?",
        ),
        turn_config=TurnConfig(
            show_setup_events=False,
            enable_token_streaming=True,
        ),
    )

ui.run()
```

That's it! You now have an agent-driven chat interface.

## Response Types

Agents can return any combination of:

- **Text (str)**: Rendered as markdown
- **DataFrames (pd.DataFrame)**: Rendered as interactive tables
- **Plotly Figures (go.Figure)**: Rendered as interactive charts
- **Response**: Multi-part container for combining types

```python
from agex_ui.core.responses import Response

# Single type
return "Simple text response"

# Multiple types in one response
return Response(parts=[
    "Analysis complete:",
    dataframe,
    plotly_figure,
    "Additional notes...",
])
```

## Configuration Options

### ChatInterfaceConfig

Customize the chat interface appearance:

```python
ChatInterfaceConfig(
    header_bg_color="#5894c8",     # Header background color
    title="My App",                 # Header title
    page_title="My App",            # Browser page title
    greeting="Welcome!",            # Initial bot message
    robot_avatar="assets/robot.png",
    human_avatar="assets/human.png",
    dark_mode=True,                  # Start in dark mode
)
```

### TurnConfig

Customize turn execution behavior:

```python
TurnConfig(
    show_setup_events=False,        # Show/hide agent setup events
    enable_token_streaming=True,    # Enable real-time token streaming
    auto_scroll=True,                # Auto-scroll to new messages
    collapse_agent_activity=True,   # Start with activity collapsed
)
```

## Example Agents

### TMNT Demo

The `tmnt` package demonstrates a calendar assistant using local iCal files. No OAuth or external API setup required beyond your LLM credentials.

- Uses [`calgebra`](https://github.com/ashenfad/calgebra) for timeline operations
- Showcases multi-part responses (text + tables + charts)
- Demonstrates state persistence with `Versioned` storage

```bash
python -m agex_ui.tmnt.main
```

### Google Calendar Assistant (Advanced)

The `cal` package demonstrates Google Calendar integration.

> [!WARNING]
> Requires [Google Calendar OAuth credentials](https://google-calendar-simple-api.readthedocs.io/en/latest/getting_started.html#credentials).

```bash
python -m agex_ui.cal.main
```

## Design Philosophy

**Agent-Agnostic Core**: The framework doesn't create or configure agents. You define your agent with domain-specific setup, then pass its task function to the UI framework.

**Separation of Concerns**:
- **Core**: UI orchestration, rendering, event handling (framework layer)
- **Templates**: Reusable layouts and configurations (presentation layer)
- **Your Agent**: Domain logic, tools, prompts (application layer)

This architecture ensures the framework remains flexible and reusable across different agent implementations.

## Learn More

- **agex Documentation**: [ashenfad.github.io/agex/](https://ashenfad.github.io/agex/)
- **calgebra Documentation**: [github.com/ashenfad/calgebra](https://github.com/ashenfad/calgebra)
- **NiceGUI Documentation**: [nicegui.io](https://nicegui.io/)

## License

MIT License - See [LICENSE](LICENSE) file for details.
import nicegui
import asyncio

from functools import partial
from nicegui import ui
from agex import Agent, connect_llm, pprint_events, summarize_capabilities
from agex.helpers import register_stdlib, register_plotly
from agex_ui.lorem_ipsum.primer import PRIMER

agent = Agent(
    name="lorem_ipsum",
    primer=PRIMER,
    llm_client=connect_llm(
        provider="openai",
        model="gpt-5",
        reasoning_effort="medium",
    ),
)


# enable stdlib & plotting via helpers
register_stdlib(agent)
register_plotly(agent)

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
    use_cache=True, # cache to `.agex` so we only build this once
)

@agent.task
def create_page(page: str, col: ui.column):
    """Create a realistic stand-in page via nicegui given the page name."""
    pass


COL_STYLE = """
display: flex; 
flex-direction: column; 
align-items: center; 
justify-content: center; 
width: 100vw; 
height: 100vh; 
position: fixed; 
top: 0; 
left: 0; 
text-align: center;
"""


@ui.page("/{page:path}")
async def lorem_router(page: str):
    """Dynamic lorem ipsum page route handler."""
    # Configure basic page styles
    ui.query("body").style(
        "background-color: #f8f9fa; margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;"
    )
    ui.page_title(f"Loading {page.title()}...")

    # Create main page container
    with ui.element() as main_container:
        # Show loading state while agent works
        with ui.column().style(COL_STYLE) as loading_container:
            ui.spinner(size="lg")
            ui.label(f"Generating {page.title()} page...").style(
                "font-size: 1.125rem; margin-top: 1rem; text-align: center;"
            )

    # Create hidden container for the actual page content
    with ui.element().style("display: none") as temp_container:
        page_column = ui.column().classes("w-full")

    pprint = partial(pprint_events, verbosity="verbose", truncate_code_lines=100)

    # Run the agent task in background thread to avoid blocking UI
    await asyncio.to_thread(create_page, page, page_column, on_event=pprint)

    # Replace loading screen with actual content
    loading_container.delete()
    with main_container:
        page_column.move(main_container)

    # Update page title
    ui.page_title(f"{page.title()} - Your App")

    # Clean up
    temp_container.delete()


ui.run()

"""Session management drawer component (branch-based)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from nicegui import app, ui

if TYPE_CHECKING:
    from agex import Agent

from agex.state import Staged
from agex_ui.core.sessions import (
    CURRENT_BRANCH_KEY,
    SESSION_TITLE_KEY,
    SESSION_UPDATED_KEY,
    generate_branch_name,
    get_session_title,
    list_sessions,
)
from agex_ui.core.utils import format_timestamp, parse_timestamp


@dataclass
class SessionPanelResult:
    """Result from setup_session_panel."""
    drawer: ui.element
    refresh: Callable[[], None]


def setup_session_panel(
    agent: "Agent",
    namespace: str,
    current_branch: str,
    toggle_btn: ui.button,
) -> SessionPanelResult:
    """Setup the session management drawer.

    Returns:
        SessionPanelResult with drawer element and refresh callback
    """
    state: Staged = agent.state(namespace)

    drawer_open = app.storage.user.get("session_drawer_open", True)

    with ui.left_drawer(value=drawer_open).props("bordered user-select=none").style(
        "background-color: var(--bg-card); color: var(--text-primary); border-right: 1px solid var(--border-default);"
    ) as session_drawer:
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("History").classes("text-h6 q-md").style("color: var(--text-primary)")

            async def clear_history():
                with ui.dialog() as dialog, ui.card():
                    ui.label("Are you sure you want to clear all history? This cannot be undone.")
                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=dialog.close).props("flat")
                        ui.button("Clear", on_click=lambda: dialog.submit(True)).props("flat color=negative")

                if await dialog:
                    # Delete all non-main branches, create a fresh chat
                    for branch in state.list_branches():
                        if branch != "main" and branch != current_branch:
                            state.delete_branch(branch)
                    # Create new branch, switch to it, then delete old current
                    new_branch = generate_branch_name()
                    initial = state.versioned.initial_commit
                    state.create_branch(new_branch, at=initial)
                    state.switch_branch(new_branch)
                    if current_branch != "main":
                        state.delete_branch(current_branch)
                    app.storage.user[CURRENT_BRANCH_KEY] = new_branch
                    ui.navigate.to("/")

            with ui.row().classes("gap-0"):
                ui.button(icon="delete_sweep", on_click=clear_history).props("flat round dense color=grey").tooltip("Clear all")

        # New Chat Button
        def create_new_chat():
            new_branch = generate_branch_name()
            initial = state.versioned.initial_commit
            state.create_branch(new_branch, at=initial)
            state.switch_branch(new_branch)
            now = datetime.now(timezone.utc).isoformat()
            state[SESSION_UPDATED_KEY] = now
            state.commit()
            app.storage.user[CURRENT_BRANCH_KEY] = new_branch
            ui.navigate.to(f"/?branch={new_branch}")

        ui.button("New Chat", icon="add", on_click=create_new_chat).classes("w-full mb-4").props("outline")

        # Session List Container
        session_list_container = ui.column().classes("w-full gap-1")

        def refresh_session_list():
            session_list_container.clear()
            sessions = list_sessions(state)
            active = app.storage.user.get(CURRENT_BRANCH_KEY)
            with session_list_container:
                for s in sessions:
                    branch = s["branch"]
                    is_active = branch == active
                    row_classes = "session-item--active" if is_active else "session-item"

                    with ui.row().classes(f"w-full items-center p-2 rounded cursor-pointer no-wrap {row_classes}") as row:

                        def open_session(b=branch):
                            if b != active:
                                state.switch_branch(b)
                                app.storage.user[CURRENT_BRANCH_KEY] = b
                                ui.navigate.to(f"/?branch={b}")

                        row.on("click", open_session)

                        with ui.column().classes("flex-grow gap-1").style("min-width: 0"):
                            MAX_LENGTH = 35
                            title = s["title"]
                            display_name = title if len(title) <= MAX_LENGTH else title[:MAX_LENGTH] + "..."
                            label = ui.label(display_name).classes("text-sm font-medium w-full leading-tight").style("cursor: pointer;")
                            if len(title) > MAX_LENGTH:
                                label.tooltip(title)

                            with ui.row().classes("gap-1 items-center justify-between w-full"):
                                ts_val = parse_timestamp(s["updated"])
                                if ts_val:
                                    ui.label(format_timestamp(ts_val)).classes("text-xs text-gray-500 truncate")

                                with ui.row().classes("gap-0 items-center"):
                                    # Fork (only for active session)
                                    if is_active:
                                        def fork_session(b=branch):
                                            new_branch = generate_branch_name()
                                            # Fork from current HEAD
                                            state.create_branch(new_branch)
                                            state.switch_branch(new_branch)
                                            # Copy title
                                            src_title = get_session_title(state, b)
                                            now = datetime.now(timezone.utc).isoformat()
                                            state[SESSION_TITLE_KEY] = f"{src_title} (fork)"
                                            state[SESSION_UPDATED_KEY] = now
                                            state.commit()
                                            app.storage.user[CURRENT_BRANCH_KEY] = new_branch
                                            ui.navigate.to(f"/?branch={new_branch}")

                                        ui.button(icon="fork_right", on_click=fork_session).props("flat round dense size=xs color=grey").tooltip("Fork session")

                                    # Delete
                                    def delete_session(b=branch, t=s["title"]):
                                        if b == active:
                                            # Switch away first
                                            remaining = [x for x in state.list_branches() if x != b and x != "main"]
                                            if remaining:
                                                state.switch_branch(remaining[0])
                                                app.storage.user[CURRENT_BRANCH_KEY] = remaining[0]
                                            else:
                                                # Create fresh chat
                                                nb = generate_branch_name()
                                                initial = state.versioned.initial_commit
                                                state.create_branch(nb, at=initial)
                                                state.switch_branch(nb)
                                                now = datetime.now(timezone.utc).isoformat()
                                                state[SESSION_UPDATED_KEY] = now
                                                state.commit()
                                                app.storage.user[CURRENT_BRANCH_KEY] = nb
                                        state.delete_branch(b)
                                        ui.notify(f"Deleted '{t}'")
                                        if b == current_branch:
                                            ui.navigate.to("/")
                                        else:
                                            refresh_session_list()

                                    ui.button(icon="delete", on_click=delete_session).props("flat round dense size=xs color=grey")

        # Initial render
        refresh_session_list()

    # Persist drawer state changes
    session_drawer.on_value_change(lambda e: app.storage.user.update({"session_drawer_open": e.value}))

    toggle_btn.on("click", lambda: session_drawer.toggle())

    return SessionPanelResult(drawer=session_drawer, refresh=refresh_session_list)

"""File manager drawer component."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from nicegui import app, ui, events as nicegui_events

if TYPE_CHECKING:
    from agex import Agent

from agex.state import Staged
from agex_ui.core.user_bubble import render_user_action_bubble


@dataclass
class FileManagerResult:
    """Result from setup_file_manager."""
    drawer: ui.element
    refresh: Callable[[], None]


def setup_file_manager(
    agent: "Agent",
    namespace: str,
    chat_messages: ui.column,
    file_badge: ui.label | None = None,
    refresh_session_list_callback: Callable[[], None] | None = None,
) -> FileManagerResult:
    """Setup the file manager drawer.
    
    Returns:
        FileManagerResult with drawer element and refresh callback
    """
    # Load persistence state
    drawer_open = app.storage.user.get("file_drawer_open", False)

    with ui.right_drawer(value=drawer_open).props("bordered user-select=none").style(
        "background-color: var(--bg-card); color: var(--text-primary); border-left: 1px solid var(--border-default);"
    ) as drawer:
        ui.label("Files").classes("text-h6 q-md").style("color: var(--text-primary)")
        
        # UI State
        selected_files = set()
        file_checkboxes = {} # filename -> checkbox
        
        # File List Container
        file_list_container = ui.column().classes("w-full gap-1")

        def refresh_file_list():
            try:
                # Get fresh fs
                fs = agent.fs(namespace)
            except ValueError:
                # No FS configured
                if file_badge:
                    file_badge.set_text("0")
                    file_badge.set_visibility(False)
                    file_badge.update()
                return

            try:
                # List all entries recursively, then filter to files only
                all_entries = fs.list(recursive=True)
                files = [entry for entry in all_entries if fs.isfile(entry)]
            except Exception:
                 # VFS might not be ready or configured
                files = []

            file_list_container.clear()
            file_checkboxes.clear()
            selected_files.clear()

            if not files:
                with file_list_container:
                    ui.label("No files").style("color: var(--text-muted)").classes("italic")
                if file_badge:
                    file_badge.set_text("0")
                    file_badge.set_visibility(False)
                    file_badge.update()
                update_bulk_buttons()
                return

            with file_list_container:
                for filename in sorted(files):
                    with ui.row().classes("items-center w-full no-wrap"):
                        def on_check(e, name=filename):
                            if e.value:
                                selected_files.add(name)
                            else:
                                selected_files.discard(name)
                            update_bulk_buttons()

                        cb = ui.checkbox(on_change=on_check).props("dense")
                        file_checkboxes[filename] = cb
                        ui.label(filename).style("color: var(--text-primary)").classes("text-sm ellipsis overflow-hidden")

            # Update badge
            if file_badge:
                count = len(files)
                file_badge.set_text(str(count))
                file_badge.set_visibility(count > 0)
                file_badge.update()

            update_bulk_buttons()

        def update_bulk_buttons():
            count = len(selected_files)
            delete_btn.text = f"Delete ({count})"
            download_btn.text = f"Download ({count})"
            
            if count > 0:
                delete_btn.enable()
                download_btn.enable()
            else:
                delete_btn.disable()
                download_btn.disable()

        async def handle_multi_upload(e: nicegui_events.MultiUploadEventArguments):
            """Handle multiple file uploads in a single batch."""
            if not e.files:
                return

            files_dict = {}
            filenames = []
            
            for f in e.files:
                content = await f.read()
                files_dict[f.name] = content
                filenames.append(f.name)
            
            try:
                state = agent.state(namespace)
                
                # Capture commit BEFORE changes if versioned
                revert_commit = None
                if isinstance(state, Staged):
                    revert_commit = state.current_commit

                fs = agent.fs(namespace)
                # Write all files at once
                fs.write_many(files_dict)
            except ValueError:
                ui.notify("Agent does not have a filesystem configured", type="warning")
                upload_element.reset()
                return
            except Exception as e:
                ui.notify(f"Failed to upload files: {e}", type="negative")
                upload_element.reset()
                return

            refresh_file_list()

            # Single bubble for all files
            if len(filenames) == 1:
                msg = f"**Uploaded:** `{filenames[0]}`"
            else:
                file_list = ", ".join(f"`{filename}`" for filename in filenames)
                msg = f"**Uploaded {len(filenames)} files:** {file_list}"

            await render_user_action_bubble(
                chat_messages, msg, agent, namespace,
                revert_commit=revert_commit,
                refresh_file_list_callback=refresh_file_list,
                refresh_session_list_callback=refresh_session_list_callback
            )
            ui.notify(f"Uploaded {len(filenames)} file{'s' if len(filenames) > 1 else ''}")
            upload_element.reset()

        async def handle_delete_selected():
            to_delete = list(selected_files)
            if not to_delete:
                return
            
            fs = agent.fs(namespace)
            state = agent.state(namespace)

            # Capture commit BEFORE changes if versioned
            revert_commit = None
            if isinstance(state, Staged):
                revert_commit = state.current_commit

            fs.remove_many(to_delete)
            refresh_file_list()

            # Render bubble
            items = [f"`{item}`" for item in to_delete]
            await render_user_action_bubble(
                chat_messages, f"**Removed:** {', '.join(items)}", agent, namespace,
                revert_commit=revert_commit,
                refresh_file_list_callback=refresh_file_list,
                refresh_session_list_callback=refresh_session_list_callback
            )
            ui.notify(f"Deleted {len(to_delete)} files")

        async def handle_download_selected():
            import os
            fs = agent.fs(namespace)
            for filename in list(selected_files):
                try:
                    content_bytes = fs.read(filename)
                    # Use basename for download (main.py instead of app/main.py)
                    download_name = os.path.basename(filename)
                    ui.download(content_bytes, download_name)
                except Exception as e:
                    ui.notify(f"Error downloading {filename}: {e}", type="negative")

        # --- UI Layout ---
        
        # Bulk Actions
        with ui.row().classes("w-full gap-2 mb-2"):
            delete_btn = ui.button("Delete (0)", on_click=handle_delete_selected).props("outline color=negative dense").classes("flex-grow")
            delete_btn.disable()
            
            download_btn = ui.button("Download (0)", on_click=handle_download_selected).props("outline color=primary dense").classes("flex-grow")
            download_btn.disable()

        # Upload Area
        upload_element = ui.upload(
            label="Upload files",
            multiple=True,
            auto_upload=True,
            on_multi_upload=handle_multi_upload
        ).props("flat bordered").classes("w-full mb-4")

        ui.separator().classes("mb-2")

        refresh_file_list()
        
        # Persist drawer state changes
        drawer.on_value_change(lambda e: app.storage.user.update({"file_drawer_open": e.value}))

        return FileManagerResult(drawer=drawer, refresh=refresh_file_list)

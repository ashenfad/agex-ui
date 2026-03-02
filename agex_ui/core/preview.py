"""Live preview infrastructure for agent-built NiceGUI apps."""

import re
import time
import traceback
from typing import TYPE_CHECKING, Callable
from nicegui import ui, app

if TYPE_CHECKING:
    from agex import Agent

import nicegui as _nicegui
from agex.eval.bridge.policy import translate_policy
from agex.fs import VirtualFS
from sandtrap import sandbox as create_sandbox

from agex_ui.core.theme import THEME_CSS, THEME_JS
from agex_ui.core.user_bubble import render_user_action_bubble


def _prettify_html(html: str, indent: str = "  ") -> str:
    """Format HTML for readability.

    Adds newlines and indentation to make HTML easier to inspect.
    Handles void elements (img, br, meta, etc.) correctly.
    """
    void_elements = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    }

    # Split into tokens (tags and text)
    tokens = re.split(r"(<[^>]+>)", html)

    result = []
    level = 0

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        if token.startswith("<"):
            tag_match = re.match(r"<(/?)([a-zA-Z!][a-zA-Z0-9:-]*)", token)
            if tag_match:
                is_closing = tag_match.group(1) == "/"
                tag_name = tag_match.group(2).lower()

                if is_closing:
                    level = max(0, level - 1)

                result.append(indent * level + token)

                if not is_closing and tag_name not in void_elements and not token.endswith("/>"):
                    if not tag_name.startswith("!"):  # Skip doctype, comments
                        level += 1
            else:
                result.append(indent * level + token)
        else:
            # Text content
            if token:
                result.append(indent * level + token)

    return "\n".join(result)


def register_preview_route(
    agent: "Agent",
    namespace: str,
):
    """Register the /preview/{session_id} route.

    Each request creates a fresh sandbox with copied app files from the main
    agent's VFS. This ensures clean state on each preview refresh.

    Args:
        agent: The main agent (app files are read from its VFS)
        namespace: Fixed namespace for state resolution
    """
    @ui.page('/preview/{session_id}')
    def preview_page(session_id: str):
        # Inject theme CSS and JS so agent apps can use CSS variables
        ui.add_head_html(f"<style>{THEME_CSS}</style>")
        ui.add_head_html(f"<script>{THEME_JS}</script>")

        # Fix viewport height - set CSS variable based on actual iframe height
        # This allows apps to use var(--iframe-vh) instead of vh units
        viewport_fix = """
        <style>
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
            /* Ensure NiceGUI content fills the iframe for proper chart sizing */
            .nicegui-content {
                height: 100% !important;
                max-height: 100% !important;
                overflow: auto;
            }
        </style>
        <script>
            (function() {
                function setIframeVh() {
                    // Set --iframe-vh to 1% of the actual iframe height
                    const vh = window.innerHeight * 0.01;
                    document.documentElement.style.setProperty('--iframe-vh', vh + 'px');
                }
                setIframeVh();
                window.addEventListener('resize', setIframeVh);
            })();
        </script>
        """
        ui.add_head_html(viewport_fix)

        # Initialize theme, console capture, and listen for changes from parent window
        init_script = """
        <script>
            (function() {
                // Initialize theme from localStorage (syncs with main app)
                initTheme(true);

                // Capture console logs
                window.__consoleBuffer = [];
                const maxLogLines = 500;

                ['log', 'warn', 'error', 'info'].forEach(function(method) {
                    const original = console[method];
                    console[method] = function(...args) {
                        original.apply(console, args);

                        // Format log entry
                        const timestamp = new Date().toISOString();
                        const message = args.map(function(arg) {
                            if (typeof arg === 'object') {
                                try { return JSON.stringify(arg); }
                                catch (e) { return String(arg); }
                            }
                            return String(arg);
                        }).join(' ');

                        const entry = '[' + timestamp + '] ' + method.toUpperCase() + ': ' + message;
                        window.__consoleBuffer.push(entry);

                        // Keep only last N lines
                        if (window.__consoleBuffer.length > maxLogLines) {
                            window.__consoleBuffer = window.__consoleBuffer.slice(-maxLogLines);
                        }
                    };
                });

                // Listen for theme changes from parent window
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'theme-change') {
                        const newTheme = event.data.theme;
                        document.documentElement.setAttribute('data-theme', newTheme);
                        if (newTheme === 'dark') {
                            document.body.classList.add('dark');
                        } else {
                            document.body.classList.remove('dark');
                        }
                    }
                });
            })();
        </script>
        """
        ui.add_head_html(init_script)

        # Apply background that respects light/dark mode
        ui.query("body").style("background-color: var(--bg-primary); margin: 0; padding: 0;")

        try:
            # Check if main agent has app files
            main_fs = agent.fs(namespace)
            if not main_fs.exists('app/main.py'):
                with ui.column().classes("w-full h-full items-center justify-center"):
                    ui.label("No app yet - ask the agent to build one!").classes(
                        "italic"
                    ).style("color: var(--text-primary)")
                return

            # Build sandbox policy: agent's policy + NiceGUI modules
            policy = translate_policy(agent)
            policy.module(_nicegui, name="nicegui", recursive=True)

            # Snapshot the agent's VFS into an isolated copy so preview
            # code can read files but not modify agent state.
            state = agent.state(namespace)
            snapshot = {
                k: state.get(k)
                for k in state.keys()
                if k.startswith(VirtualFS.PREFIX) or k == VirtualFS.METADATA_KEY
            }
            preview_fs = VirtualFS(snapshot)

            # Create raw-mode sandbox (no wrappers — NiceGUI objects keep full API)
            sb = create_sandbox(policy, mode="raw", filesystem=preview_fs)

            # Read app code from main agent's VFS and execute
            code = main_fs.read("app/main.py").decode("utf-8")
            result = sb.exec(code)
            if result.error:
                raise result.error

        except Exception as e:
            # Get full traceback
            error_text = traceback.format_exc()

            # Write error to main agent's VFS for debugging
            try:
                main_fs = agent.fs(namespace)
                main_fs.write("debug/error.txt", error_text.encode("utf-8"))
            except Exception:
                pass  # Don't fail if we can't write the error file

            # Show error as modal dialog floating above app content
            with ui.dialog(value=True).props("persistent maximized") as dialog:
                with ui.card().classes("w-full h-full").style("max-width: 95%; max-height: 90%;"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("App Error").classes("text-red-500 font-bold text-lg")
                        ui.button(icon="close", on_click=dialog.close).props("flat round dense")
                    with ui.scroll_area().classes("w-full").style("height: 400px; margin-top: 12px;"):
                        ui.code(error_text).classes("text-sm whitespace-pre-wrap")


def create_preview_panel(
    session_id: str,
    agent: "Agent",
    namespace: str,
    chat_messages: ui.column,
    on_refresh: Callable[[], None] | None = None,
    on_debug_captured: Callable[[], None] | None = None,
) -> tuple[ui.element, Callable[[], None]]:
    """Create the preview iframe panel.

    Args:
        session_id: Current session ID for preview route
        agent: The main agent (for VFS access when capturing debug info)
        namespace: Namespace for VFS operations
        chat_messages: Chat messages container for rendering debug bubbles
        on_refresh: Optional callback when refresh is triggered
        on_debug_captured: Optional callback when debug info is captured

    Returns:
        (container, refresh_fn) - The panel element and a function to refresh it
    """
    preview_url = f"/preview/{session_id}"

    with ui.column().classes("w-full h-full p-0 m-0 gap-0 overflow-hidden") as container:
        # Toolbar (compact)
        with ui.row().classes("w-full items-center py-1 px-2 border-b gap-1 shrink-0").style(
            "background-color: var(--bg-secondary); color: var(--text-primary); border-color: var(--border-default); min-height: 32px;"
        ):
            ui.icon("visibility", size="xs").style("color: var(--text-secondary)")
            ui.label("Preview").classes("text-xs font-medium")
            ui.element("div").classes("flex-grow")
            ui.button(icon="bug_report", on_click=lambda: capture_debug()).props(
                "flat round dense size=sm"
            ).style("color: var(--text-primary)").tooltip("Share debug")
            ui.button(icon="refresh", on_click=lambda: refresh_iframe()).props(
                "flat round dense size=sm"
            ).style("color: var(--text-primary)").tooltip("Refresh")

        # Iframe - using inline style to ensure it fills the container
        iframe = ui.html(
            f'<iframe id="preview-iframe" src="{preview_url}" style="width: 100%; height: 100%; border: none;"></iframe>',
            sanitize=False
        ).classes("w-full h-full m-0 p-0").style("width: 100%; height: 100%;")

    def refresh_iframe():
        """Refresh the preview iframe."""
        # Use a timestamp to bypass browser caching
        t = int(time.time() * 1000)
        iframe.content = f'<iframe id="preview-iframe" src="{preview_url}?t={t}" style="width: 100%; height: 100%; border: none;"></iframe>'
        iframe.update()
        if on_refresh:
            on_refresh()

    async def capture_debug():
        """Capture DOM, console logs, and sandbox debug files to main agent's VFS."""
        # Capture DOM via JavaScript
        dom_js = """
        (function() {
            const iframe = document.getElementById('preview-iframe');
            if (!iframe || !iframe.contentDocument) {
                return '<html><body>Could not access iframe content</body></html>';
            }
            return iframe.contentDocument.documentElement.outerHTML;
        })();
        """
        try:
            dom_html = await ui.run_javascript(dom_js)
        except Exception as e:
            dom_html = f"<html><body>Error capturing DOM: {e}</body></html>"

        # Capture console logs from iframe's buffer
        console_js = """
        (function() {
            const iframe = document.getElementById('preview-iframe');
            if (!iframe || !iframe.contentWindow || !iframe.contentWindow.__consoleBuffer) {
                return '';
            }
            return iframe.contentWindow.__consoleBuffer.join('\\n');
        })();
        """
        try:
            console_logs = await ui.run_javascript(console_js)
        except Exception:
            console_logs = ""

        # Write DOM and console to main agent's VFS
        fs = agent.fs(namespace)
        pretty_dom = _prettify_html(dom_html)
        files_to_write = {"debug/dom.html": pretty_dom.encode("utf-8")}
        if console_logs and console_logs.strip():
            files_to_write["debug/console.log"] = console_logs.encode("utf-8")

        fs.write_many(files_to_write)

        # Format file list for chat bubble
        filenames = sorted(files_to_write.keys())
        file_list = ", ".join(f"`{f}`" for f in filenames)
        markdown_content = f"**Shared:** {file_list}"

        # Render as a chat bubble (like file uploads)
        await render_user_action_bubble(
            chat_messages=chat_messages,
            markdown_content=markdown_content,
            agent=agent,
            namespace=namespace,
            refresh_file_list_callback=on_debug_captured,
        )

    return container, refresh_iframe

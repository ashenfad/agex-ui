"""Theme management for agex-ui.

Provides a centralized theme system with CSS variables for light/dark mode support.
"""

from nicegui import ui

# CSS variables for theming
THEME_CSS = """
:root {
    /* Light mode (default) */
    --bg-primary: #ffffff;
    --bg-secondary: #f6f8fa;
    --bg-tertiary: #f1f3f4;
    --bg-card: #ffffff;
    --bg-code: #f6f8fa;

    --text-primary: #24292e;
    --text-secondary: #6a737d;
    --text-muted: #959da5;

    --border-default: #e1e4e8;
    --border-strong: #d1d5da;

    --accent-primary: #5894c8;
    --accent-secondary: #6f42c1;
    --accent-success: #28a745;
    --accent-warning: #ffc107;
    --accent-error: #dc3545;

    --diff-added-bg: rgba(40, 167, 69, 0.15);
    --diff-removed-bg: rgba(220, 53, 69, 0.15);
    --diff-added-highlight: rgba(40, 167, 69, 0.4);
    --diff-removed-highlight: rgba(220, 53, 69, 0.4);

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
}

[data-theme="dark"] {
    --bg-primary: #24292f;
    --bg-secondary: #151a20;
    --bg-tertiary: #20252c;
    --bg-card: #161b22;
    --bg-code: #282f38;

    --text-primary: #c9d1d9;
    --text-secondary: #6b747e;
    --text-muted: #6e7681;

    --border-default: #22282f;
    --border-strong: #484f58;

    --accent-primary: #58a6ff;
    --accent-secondary: #a371f7;
    --accent-success: #3fb950;
    --accent-warning: #d29922;
    --accent-error: #f85149;

    --diff-added-bg: rgba(35, 110, 45, 0.4);
    --diff-removed-bg: rgba(140, 40, 35, 0.4);
    --diff-added-highlight: rgba(35, 110, 45, 0.7);
    --diff-removed-highlight: rgba(140, 40, 35, 0.7);

    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
}

/* Apply theme to body */
body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    transition: background-color 0.2s ease, color 0.2s ease;
}

/* Responsive content container - use vw to avoid parent-based sizing issues */
.content-container {
    width: min(calc(100vw - 32px), 1000px);
}

/* Allow chat bubble content to scroll if too wide */
.q-message-text {
    max-width: 100%;
    min-width: 0;
    overflow-x: auto;
}

/* Prevent code/pre blocks from expanding chat bubbles */
.q-message-text pre,
.q-message-text code {
    max-width: 100%;
    min-width: 0;
    overflow-x: auto;
}

.q-message-text pre {
    white-space: pre;
}

/* Break intrinsic sizing on all ancestors within message */
.q-message-container,
.q-message-container > div {
    min-width: 0;
}

/* Force agent messages to use full container width ONLY if they have wide content */
.wide-message.q-message-received,
.wide-message.q-message-sent {
    width: 100% !important;
}

.wide-message.q-message-received .q-message-container,
.wide-message.q-message-sent .q-message-container {
    max-width: 100% !important;
}

/* Target the anonymous div between q-message-container and q-message-text 
   and force it to fill the available space */
.wide-message.q-message-received .q-message-container > div,
.wide-message.q-message-sent .q-message-container > div {
    flex-grow: 1 !important;
    width: 100% !important;
    min-width: 0 !important;
}

/* Ensure the text bubble itself expands to fill the anonymous container */
.wide-message .q-message-text {
    width: 100% !important;
}

/* Remove spacing between markdown elements in chat bubbles */
.q-message-text p,
.q-message-text .markdown p {
    margin: 0 0 0.5em 0;
}

.q-message-text p:last-child,
.q-message-text .markdown p:last-child {
    margin-bottom: 0;
}

/* Aggressively remove margins from all NiceGUI component wrappers */
.q-message-text > div,
.q-message-text .markdown,
.q-message-text .nicegui-markdown,
.q-message-text .nicegui-table,
.q-message-text .nicegui-plotly {
    margin: 0 !important;
    padding: 0 !important;
}

/* Remove top/bottom margins from first/last elements in chat bubbles */
.q-message-text > *:first-child,
.q-message-text .markdown > *:first-child {
    margin-top: 0 !important;
}

.q-message-text > *:last-child,
.q-message-text .markdown > *:last-child {
    margin-bottom: 0 !important;
}

/* Remove gaps between all direct children */
.q-message-text > * {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* Plotly theme switching - use absolute positioning to stack charts */
.plotly-container {
    position: relative;
}

.plotly-light-mode {
    position: relative;
    z-index: 1;
}

.plotly-dark-mode {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    visibility: hidden;
    z-index: 0;
}

[data-theme="dark"] .plotly-light-mode {
    visibility: hidden;
    z-index: 0;
}

[data-theme="dark"] .plotly-dark-mode {
    visibility: visible;
    z-index: 1;
}

/* Themed card styles */
.themed-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    box-shadow: var(--shadow-sm);
}

/* Themed event card (for ActionEvent/OutputEvent) */
.themed-event-card {
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
}

.themed-event-header {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
    font-size: 14px;
}

.themed-event-meta {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 12px;
}

/* Themed code block */
.themed-code {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
    overflow-x: auto;
    white-space: pre;
    color: var(--text-primary);
    max-width: 100%;
}

/* Pygments highlighted code - constrain width */
.highlight, .highlight pre {
    overflow-x: auto;
    max-width: 100%;
    white-space: pre;
}

/* Inline code styling (backticks) */
code:not(pre code) {
    background-color: var(--bg-code);
    border-radius: 2px;
    padding: 0.5px 0.5px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.9em;
    color: var(--accent-primary);
}

/* Themed action sections */
.themed-thinking {
    border-left: 3px solid var(--accent-secondary);
    padding-left: 12px;
    padding-right: 12px;
    margin: 8px 0;
    color: var(--text-secondary);
    overflow-x: auto;
}

.themed-thinking pre {
    overflow-x: auto;
    max-width: 100%;
    white-space: pre;
}

.themed-thinking code {
    white-space: pre;
}

.themed-output {
    border-left: 3px solid var(--accent-secondary);
    padding-left: 10px;
    margin: 8px 0;
}

/* File action badges */
.themed-files {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 4px 0;
}

.themed-file-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background-color: var(--bg-code);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--text-primary);
}

.themed-file-badge .file-mode {
    color: var(--text-secondary);
    font-size: 11px;
}

/* Chat message overrides for dark mode */
[data-theme="dark"] .q-message-text {
    background-color: #5894c8 !important;
    color: #24292e !important;
}

/* Fix bubble tip (arrow) for received messages */
[data-theme="dark"] .q-message-text--received::before {
    border-bottom-color: #5894c8 !important;
}

[data-theme="dark"] .q-message-text--sent {
    background-color: #8f8f8f !important;
    color: #ffffff !important;
}

/* Fix bubble tip (arrow) for sent messages */
[data-theme="dark"] .q-message-text--sent::before {
    border-bottom-color: #8f8f8f !important;
}

/* Agent name and timestamp */
[data-theme="dark"] .q-message-name {
    color: var(--text-secondary) !important;
}

[data-theme="dark"] .q-message-stamp {
    color: #24292e !important;
}

/* Expansion panel theming */
[data-theme="dark"] .q-expansion-item {
    background-color: var(--bg-secondary);
    border-color: var(--border-default);
    border-radius: 8px;
}

[data-theme="dark"] .q-expansion-item__container {
    background-color: var(--bg-secondary) !important;
    border-radius: 7px;
}

/* Allow horizontal scroll for long code in expansions */
.q-expansion-item__content {
    overflow-x: auto;
}

/* Compact expansion panel header - both modes */
.q-expansion-item .q-item {
    min-height: 30px;
    padding-top: 4px;
    padding-bottom: 4px;
}

/* Ensure hover highlight respects rounded corners */
[data-theme="dark"] .q-expansion-item .q-item {
    border-radius: 7px;
}

[data-theme="dark"] .q-item__label {
    color: var(--text-secondary) !important;
}

/* Table theming */
.q-table {
    max-width: 100%;
    min-width: 0;
}

.q-table__container {
    overflow-x: auto;
    max-width: 100%;
}

[data-theme="dark"] .q-table {
    background-color: var(--bg-card);
    color: var(--text-primary);
}

[data-theme="dark"] .q-table th {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
}

[data-theme="dark"] .q-table td {
    border-color: var(--border-default) !important;
}

[data-theme="dark"] .q-table__container,
[data-theme="dark"] .q-table__card {
    background-color: var(--bg-card) !important;
    border-color: var(--border-default) !important;
    color: var(--text-primary) !important;
}



/* Input field theming */
[data-theme="dark"] .q-field__control {
    background-color: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    padding-left: 8px;
    border-radius: 8px;
}

[data-theme="dark"] .q-field__native {
    color: var(--text-primary) !important;
}

[data-theme="dark"] .q-field__label {
    color: var(--text-secondary) !important;
}

/* Uploader theming */
[data-theme="dark"] .q-uploader {
    background-color: var(--bg-card) !important;
    border: 0px solid var(--border-default);
}

[data-theme="dark"] .q-uploader__header {
    background-color: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
}

[data-theme="dark"] .q-uploader__list {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

[data-theme="dark"] .q-uploader__file--img {
    color: var(--text-primary) !important;
    background-color: var(--bg-tertiary) !important;
    border-color: var(--border-default) !important;
}

[data-theme="dark"] .q-uploader__file-header {
    color: var(--text-primary) !important;
}

[data-theme="dark"] .q-uploader__file-status {
    color: var(--text-secondary) !important;
}

[data-theme="dark"] .q-uploader__dnd {
    background-color: rgba(255, 255, 255, 0.1) !important;
    color: var(--text-primary) !important;
}

/* Checkbox theming */
[data-theme="dark"] .q-checkbox__bg {
    border-color: var(--text-muted) !important;
}

[data-theme="dark"] .q-checkbox__inner--truthy .q-checkbox__bg {
    background-color: var(--accent-primary) !important;
    border-color: var(--accent-primary) !important;
    color: #ffffff !important;
}

[data-theme="dark"] .q-checkbox__inner--truthy .q-checkbox__svg {
    color: #ffffff !important;
}

/* Modal/Card theming for dark mode */
[data-theme="dark"] .q-card {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-default);
}

[data-theme="dark"] .q-dialog__inner > div {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

/* Session List Item Styling */
.session-item {
    transition: background-color 0.2s;
}

.session-item:hover {
    background-color: var(--bg-secondary);
}

.session-item--active {
    background-color: var(--accent-primary) !important;
    color: #ffffff !important;
}

/* In dark mode, active item is slate-800 */
[data-theme="dark"] .session-item--active {
    background-color: #1e293b !important; /* slate-800 */
    color: var(--text-primary) !important;
}

[data-theme="dark"] .session-item:hover {
    background-color: var(--bg-tertiary);
}
"""

# JavaScript for theme toggling
THEME_JS = """
window.toggleTheme = function() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    
    if (document.body) {
        if (newTheme === 'dark') {
            document.body.classList.add('dark');
        } else {
            document.body.classList.remove('dark');
        }
    }
    
    localStorage.setItem('agex-ui-theme', newTheme);
    return newTheme;
};

window.initTheme = function(defaultDark) {
    const saved = localStorage.getItem('agex-ui-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (defaultDark ? 'dark' : (prefersDark ? 'dark' : 'light'));
    
    document.documentElement.setAttribute('data-theme', theme);
    
    if (document.body) {
        if (theme === 'dark') {
            document.body.classList.add('dark');
        } else {
            document.body.classList.remove('dark');
        }
    }
    
    return theme;
};

"""


class ThemeManager:
    """Manages theme state and provides toggle functionality."""

    def __init__(self, dark_mode: bool = False):
        """Initialize theme manager.

        Args:
            dark_mode: Whether to start in dark mode (default: False)
        """
        self.dark_mode = dark_mode
        self._applied = False

    def apply(self):
        """Inject theme CSS and JS into the page. Call once on page load."""
        if self._applied:
            return

        ui.add_head_html(f"<style>{THEME_CSS}</style>")
        ui.add_head_html(f"<script>{THEME_JS}</script>")

        # Initialize theme immediately when script loads (not via run_javascript)
        # This inline script runs as soon as the page loads
        init_script = f"""
        <script>
            (function() {{
                initTheme({str(self.dark_mode).lower()});
            }})();
        </script>
        """
        ui.add_head_html(init_script)
        self._applied = True

    def create_toggle_button(self) -> ui.button:
        """Create a theme toggle button.

        Returns:
            A NiceGUI button that toggles between light and dark mode.
        """

        async def toggle():
            result = await ui.run_javascript("toggleTheme()")
            self.dark_mode = result == "dark"
            # Update button icon
            button.props(f"icon={'light_mode' if self.dark_mode else 'dark_mode'}")

            # Notify preview iframe of theme change
            await ui.run_javascript(f"""
                const iframe = document.getElementById('preview-iframe');
                if (iframe && iframe.contentWindow) {{
                    iframe.contentWindow.postMessage({{
                        type: 'theme-change',
                        theme: '{result}'
                    }}, '*');
                }}
            """)

        icon = "light_mode" if self.dark_mode else "dark_mode"
        button = (
            ui.button(icon=icon, on_click=toggle)
            .props("round flat color=white")
            .tooltip("Light/Dark")
        )
        return button

    def get_plotly_template(self) -> str:
        """Get the appropriate Plotly template for the current theme.

        Note: This returns the default template. For reactive updates,
        check the theme via JavaScript or pass theme state explicitly.
        """
        return "plotly_dark" if self.dark_mode else "plotly_white"

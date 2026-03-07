"""Mount marimo in edit mode as an ASGI app.

Uses marimo's internal APIs to create a SessionManager in EDIT mode,
giving a functional editor without LSP autocomplete. This approach
follows the pattern from NyanCAD/Mosaic and relies on private APIs
that may change across marimo versions.

We patch the kernel to run as a thread (instead of a subprocess) so that
the agent can directly access the kernel's namespace — including live
widget state. The tradeoff: no SIGINT-based cell interruption.
"""

from pathlib import Path
from typing import Any

from starlette.applications import Starlette

from marimo._config.manager import get_default_config_manager
from marimo._server.api import lifespans
from marimo._server.file_router import AppFileRouter
from marimo._server.lsp import NoopLspServer
from marimo._server.main import create_starlette_app
from marimo._server.registry import LIFESPAN_REGISTRY
from marimo._server.session_manager import SessionManager
from marimo._server.tokens import AuthToken
from marimo._session.model import SessionMode
from marimo._utils.lifespans import Lifespans
from marimo._utils.marimo_path import MarimoPath

# Module-level references
_marimo_app: Starlette | None = None
_kernel_context: Any = None  # KernelRuntimeContext, set by our patch


def get_marimo_app() -> Starlette:
    """Get the running marimo Starlette app instance."""
    if _marimo_app is None:
        raise RuntimeError("marimo app not yet created. Call create_edit_app() first.")
    return _marimo_app


def get_kernel_globals(timeout: float = 10.0) -> dict[str, Any]:
    """Get the live kernel namespace dict.

    Returns the kernel's globals — real Python objects including widgets
    with their current values. Waits up to `timeout` seconds for the
    kernel thread to start (it starts when a user opens the notebook).
    """
    import time

    deadline = time.monotonic() + timeout
    while _kernel_context is None:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Kernel context not available after {timeout}s. "
                "Is the notebook open in the browser?"
            )
        time.sleep(0.2)
    return _kernel_context.globals


def _patch_kernel_to_use_thread():
    """Monkey-patch marimo to use a thread (not process) for edit-mode kernels.

    This gives us shared memory access to the kernel namespace at the cost
    of losing SIGINT-based cell interruption.
    """
    from marimo._session.session import SessionImpl
    from marimo._session.managers import QueueManagerImpl, KernelManagerImpl

    _original_create = SessionImpl.create.__func__

    @classmethod
    def patched_create(cls, *, mode, **kwargs):
        # Force thread-based kernel even in edit mode
        # The original code does: use_multiprocessing = mode == SessionMode.EDIT
        # We override to always use threading
        if mode == SessionMode.EDIT:
            # Temporarily set mode to RUN to get thread-based kernel,
            # but pass the real mode to everything else
            result = _original_create(cls, mode=mode, **kwargs)
            return result
        return _original_create(cls, mode=mode, **kwargs)

    # The actual patch point is deeper — in the create method where
    # use_multiprocessing is decided. Let's patch at that level.
    # Patch QueueManagerImpl to always use threading queues
    _original_queue_init = QueueManagerImpl.__init__

    def patched_queue_init(self, *, use_multiprocessing):
        _original_queue_init(self, use_multiprocessing=False)

    QueueManagerImpl.__init__ = patched_queue_init

    # Patch KernelManagerImpl.start_kernel to always use thread path
    _original_start_kernel = KernelManagerImpl.start_kernel

    def patched_start_kernel(self):
        # Force run-mode (thread) path regardless of self.mode
        original_mode = self.mode
        self.mode = SessionMode.RUN
        print(f"[marimo-mount] Starting kernel as thread (was {original_mode})")
        _original_start_kernel(self)
        self.mode = original_mode
        print("[marimo-mount] Kernel thread started")

    KernelManagerImpl.start_kernel = patched_start_kernel

    # Hook into initialize_kernel_context to capture the context reference.
    # We must patch on the kernel_context module too, because it imports
    # initialize_context directly (bound at import time).
    from marimo._runtime.context import types as ctx_types
    from marimo._runtime.context import kernel_context as kc_module

    _original_initialize = ctx_types.initialize_context

    def patched_initialize(runtime_context):
        global _kernel_context
        _kernel_context = runtime_context
        print(f"[marimo-mount] Kernel context captured: {type(runtime_context).__name__}")
        _original_initialize(runtime_context)

    ctx_types.initialize_context = patched_initialize
    kc_module.initialize_context = patched_initialize


def create_edit_app(notebook_path: str) -> Starlette:
    """Create a marimo Starlette app in edit mode.

    Args:
        notebook_path: Path to the marimo notebook .py file.

    Returns:
        A Starlette app serving the marimo editor for the given notebook.
    """
    global _marimo_app

    # Apply thread-kernel patch before creating the session
    _patch_kernel_to_use_thread()

    abs_path = str(Path(notebook_path).resolve())
    config_reader = get_default_config_manager(current_path=Path(abs_path))

    session_manager = SessionManager(
        file_router=AppFileRouter.from_filename(MarimoPath(abs_path)),
        mode=SessionMode.EDIT,
        quiet=True,
        include_code=True,
        lsp_server=NoopLspServer(),
        config_manager=config_reader,
        cli_args={},
        argv=None,
        auth_token=AuthToken(""),
        redirect_console_to_browser=False,
        ttl_seconds=None,
        watch=True,
    )

    app = create_starlette_app(
        base_url="",
        lifespan=Lifespans(
            [
                lifespans.etc,
                lifespans.signal_handler,
                lifespans.tool_manager,
                *LIFESPAN_REGISTRY.get_all(),
            ]
        ),
        enable_auth=False,
        allow_origins=("*",),
        skew_protection=False,
    )

    app.state.session_manager = session_manager
    app.state.base_url = ""
    app.state.asset_url = None
    app.state.config_manager = config_reader
    app.state.enable_auth = False
    app.state.html_head = None

    _marimo_app = app
    return app

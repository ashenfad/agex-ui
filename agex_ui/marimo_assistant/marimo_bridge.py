"""Bridge between agex agent and marimo notebook.

Provides direct access to the live marimo kernel namespace via shared memory.
The kernel runs as a thread (not a process) in our patched edit mode, so we
can read and write real Python objects — including widget state — directly.
"""

import sys
from pathlib import Path
from typing import Any

from marimo._ai._tools.base import ToolContext
from marimo._ai._tools.tools.cells import (
    GetCellRuntimeData,
    GetCellRuntimeDataArgs,
    GetLightweightCellMap,
    GetLightweightCellMapArgs,
)
from marimo._ai._tools.tools.errors import (
    GetNotebookErrors,
    GetNotebookErrorsArgs,
)
from marimo._ai._tools.tools.notebooks import GetActiveNotebooks
from marimo._ai._tools.tools.tables_and_variables import (
    GetTablesAndVariables,
    TablesAndVariablesArgs,
)
from marimo._ai._tools.types import EmptyArgs

from agex_ui.marimo_assistant.marimo_mount import get_kernel_globals, get_marimo_app

# --- Notebook path config ---

_notebook_path: str | None = None


def set_notebook_path(path: str) -> None:
    """Set the notebook path for data access functions."""
    global _notebook_path
    _notebook_path = str(Path(path).resolve())


def _get_context() -> ToolContext:
    """Get a ToolContext from the running marimo app."""
    return ToolContext(app=get_marimo_app())


def _get_session_id() -> str:
    """Get the active session ID from marimo."""
    ctx = _get_context()
    tool = GetActiveNotebooks(ctx)
    result = tool.handle(EmptyArgs())
    notebooks = result.data.notebooks
    if not notebooks:
        raise RuntimeError("No active marimo sessions found.")
    return notebooks[0].session_id


# --- Read tools (registered as agent functions) ---


def read_cells(preview_lines: int = 20) -> str:
    """Get all cells with code previews and runtime state.

    Returns a formatted string showing each cell's code, defined variables,
    and current status (idle, running, stale, etc.).
    """
    ctx = _get_context()
    session_id = _get_session_id()

    tool = GetLightweightCellMap(ctx)
    args = GetLightweightCellMapArgs(
        session_id=session_id,
        preview_lines=preview_lines,
    )
    result = tool.handle(args)
    return str(result)


def get_cell_details(cell_ids: list[str]) -> str:
    """Get detailed runtime data for specific cells.

    Args:
        cell_ids: List of cell IDs to inspect.

    Returns detailed execution info, defined variables, and outputs.
    """
    ctx = _get_context()
    session_id = _get_session_id()

    tool = GetCellRuntimeData(ctx)
    args = GetCellRuntimeDataArgs(
        session_id=session_id,
        cell_ids=cell_ids,
    )
    result = tool.handle(args)
    return str(result)


def get_variable_info(variable_names: list[str]) -> str:
    """Get type info and schemas for notebook variables.

    Args:
        variable_names: Names of variables to inspect (e.g. ["df", "model"]).

    Returns type information, DataFrame schemas, etc.
    """
    ctx = _get_context()
    session_id = _get_session_id()

    tool = GetTablesAndVariables(ctx)
    args = TablesAndVariablesArgs(
        session_id=session_id,
        variable_names=variable_names,
    )
    result = tool.handle(args)
    return str(result)


def get_errors() -> str:
    """Get all notebook errors organized by cell.

    Returns error messages and tracebacks for any failing cells.
    """
    ctx = _get_context()
    session_id = _get_session_id()

    tool = GetNotebookErrors(ctx)
    args = GetNotebookErrorsArgs(session_id=session_id)
    result = tool.handle(args)
    return str(result)


# --- Direct kernel access (real Python objects) ---


def get_notebook_data(variable_names: list[str] | None = None) -> dict[str, Any]:
    """Get real Python objects from the live notebook kernel.

    This reads directly from the kernel's namespace — no re-execution needed.
    Objects reflect the current widget state as set by the user.

    Args:
        variable_names: Optional list of variable names to retrieve.
                       If None, returns all user-defined variables
                       (excludes private names and modules).

    Returns a dict mapping variable names to their live values
    (real DataFrames, arrays, widget objects, etc.).
    """
    glbls = get_kernel_globals()

    if variable_names is not None:
        return {name: glbls[name] for name in variable_names if name in glbls}

    # Return user-defined variables (skip private, dunder, and modules)
    import types

    result = {}
    for name, value in glbls.items():
        if name.startswith("_"):
            continue
        if isinstance(value, types.ModuleType):
            continue
        result[name] = value
    return result


def set_variable(name: str, value: Any) -> None:
    """Set a variable in the live notebook kernel.

    This directly updates the kernel namespace. Useful for setting widget
    values or injecting data. Note: this does NOT trigger marimo's reactive
    re-execution — it only sets the value in the namespace.

    Args:
        name: Variable name to set.
        value: Value to assign.
    """
    glbls = get_kernel_globals()
    glbls[name] = value


# --- Write (cell delivery via file rewrite) ---


def write_notebook(cells: list[dict[str, str]]) -> None:
    """Write cells to the notebook file.

    The marimo editor's file watcher will detect the change and update
    the live editor session.

    Args:
        cells: List of dicts, each with:
            - 'code': The Python code for the cell
            - 'name' (optional): Function name for the cell (default '_')
    """
    if _notebook_path is None:
        raise RuntimeError("Notebook path not set. Call set_notebook_path() first.")

    lines = [
        "import marimo",
        "",
        "app = marimo.App()",
        "",
    ]

    for cell in cells:
        code = cell["code"]
        name = cell.get("name", "_")

        lines.append("")
        lines.append("@app.cell")
        lines.append(f"def {name}():")
        for code_line in code.split("\n"):
            lines.append(f"    {code_line}" if code_line.strip() else "")
        lines.append("")

    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    app.run()")
    lines.append("")

    Path(_notebook_path).write_text("\n".join(lines))

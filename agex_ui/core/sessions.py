"""Branch-based session management for agex-ui.

Sessions are branches in a single kvgit store. Session metadata
(title, timestamps) is stored as special keys in each branch's state.
"""

import uuid
from typing import Any

from agex.state import Staged

# Special state keys for session metadata
SESSION_TITLE_KEY = "__session_title__"
SESSION_UPDATED_KEY = "__session_updated__"

# Browser storage key (only piece persisted in cookies)
CURRENT_BRANCH_KEY = "current_branch"


def generate_branch_name() -> str:
    """Generate a unique branch name for a new session."""
    return f"chat-{uuid.uuid4().hex[:8]}"


def get_session_title(state: Staged, branch: str) -> str:
    """Read session title from a branch without switching."""
    title = state.peek(SESSION_TITLE_KEY, branch=branch)
    return title if title else "New Chat"


def get_session_updated(state: Staged, branch: str) -> str | None:
    """Read session updated timestamp from a branch without switching."""
    return state.peek(SESSION_UPDATED_KEY, branch=branch)


def list_sessions(state: Staged) -> list[dict[str, Any]]:
    """List all sessions (branches) with metadata.

    Returns list of dicts: {branch, title, updated}.
    Sorted by updated timestamp (most recent first).
    Excludes the ``main`` branch (used only as fork root).
    """
    sessions = []
    for branch in state.list_branches():
        if branch == "main":
            continue
        sessions.append({
            "branch": branch,
            "title": get_session_title(state, branch),
            "updated": get_session_updated(state, branch),
        })
    sessions.sort(key=lambda s: s["updated"] or "", reverse=True)
    return sessions

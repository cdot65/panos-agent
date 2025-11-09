"""Store context for accessing BaseStore from anywhere in the execution context.

Provides thread-safe access to the current BaseStore instance using contextvars.
This allows subgraphs and tools to access the store without explicit passing.
"""

import contextvars
from typing import Optional

from langgraph.store.base import BaseStore

# Context variable to store current BaseStore instance
_current_store: contextvars.ContextVar[Optional[BaseStore]] = contextvars.ContextVar(
    "_current_store", default=None
)


def set_store(store: Optional[BaseStore]) -> None:
    """Set the current store instance in context.

    Args:
        store: BaseStore instance or None to clear
    """
    _current_store.set(store)


def get_store() -> Optional[BaseStore]:
    """Get the current store instance from context.

    Returns:
        BaseStore instance if set, None otherwise
    """
    return _current_store.get()

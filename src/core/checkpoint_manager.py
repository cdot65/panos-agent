"""Checkpoint manager for persistent SQLite storage.

Provides utilities for managing LangGraph checkpoints with SQLite backend.
"""

import logging
import sqlite3
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)


def get_checkpoint_db_path() -> Path:
    """Get path to checkpoint database file.

    Returns:
        Path to checkpoints.db in data/ directory
    """
    # Get project root (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "checkpoints.db"
    return db_path


# Create checkpoint directory at module import time to avoid blocking calls in async context
_CHECKPOINT_DB_PATH = get_checkpoint_db_path()
_CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
logger.debug(f"Checkpoint database path: {_CHECKPOINT_DB_PATH}")


def get_checkpointer() -> SqliteSaver:
    """Get SQLite checkpointer instance (synchronous).

    Creates persistent checkpoint storage in data/checkpoints.db.
    Checkpoints survive application restarts and enable:
    - Resume from failures
    - Time-travel debugging
    - Checkpoint history inspection

    Returns:
        SqliteSaver instance configured for persistent storage

    Example:
        >>> checkpointer = get_checkpointer()
        >>> graph = workflow.compile(checkpointer=checkpointer)
    """
    # Create SQLite connection for persistent storage
    # check_same_thread=False allows connection to be used across threads
    conn = sqlite3.connect(str(_CHECKPOINT_DB_PATH), check_same_thread=False)

    # Create SqliteSaver instance with the connection
    checkpointer = SqliteSaver(conn=conn)

    logger.info(f"Initialized persistent checkpointer: {_CHECKPOINT_DB_PATH}")
    return checkpointer


async def get_async_checkpointer() -> AsyncSqliteSaver:
    """Get async SQLite checkpointer instance.

    Creates persistent checkpoint storage in data/checkpoints.db using
    async I/O for better performance with async graphs.

    Returns:
        AsyncSqliteSaver instance configured for persistent storage

    Example:
        >>> checkpointer = await get_async_checkpointer()
        >>> graph = workflow.compile(checkpointer=checkpointer)
    """
    # Create async SQLite connection
    conn = await aiosqlite.connect(str(_CHECKPOINT_DB_PATH))

    # Create AsyncSqliteSaver instance with the connection
    checkpointer = AsyncSqliteSaver(conn=conn)

    logger.info(f"Initialized async persistent checkpointer: {_CHECKPOINT_DB_PATH}")
    return checkpointer

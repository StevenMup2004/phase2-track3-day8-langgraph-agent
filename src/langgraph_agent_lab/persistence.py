"""Checkpointer adapter."""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path


def _sqlite_path(database_url: str | None) -> str:
    if not database_url:
        return "checkpoints.db"
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    if database_url.startswith("sqlite://"):
        return database_url.removeprefix("sqlite://")
    return database_url


def build_checkpointer(kind: str = "memory", database_url: str | None = None) -> object | None:
    """Return a LangGraph checkpointer.

    The starter uses MemorySaver so the lab can run without infrastructure.
    """
    if kind == "none":
        return None
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    if kind == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError as exc:
            message = "SQLite checkpointer requires: pip install langgraph-checkpoint-sqlite"
            raise RuntimeError(message) from exc

        db_path = _sqlite_path(database_url)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        if db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
        saver = SqliteSaver(conn=conn)
        setup = getattr(saver, "setup", None)
        if callable(setup):
            setup()
        return saver
    if kind == "postgres":
        try:
            module = importlib.import_module("langgraph.checkpoint.postgres")
        except ImportError as exc:
            message = "Postgres checkpointer requires: pip install langgraph-checkpoint-postgres"
            raise RuntimeError(message) from exc
        postgres_saver = module.PostgresSaver  # type: ignore[attr-defined]
        return postgres_saver.from_conn_string(database_url or "")
    raise ValueError(f"Unknown checkpointer kind: {kind}")

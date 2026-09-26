from __future__ import annotations

import sqlite3

from sqlrules_sqlite.runtime import register_sqlite_functions


def register_regexp(connection: sqlite3.Connection) -> None:
    """Backward-compatible alias for :func:`register_sqlite_functions`."""
    register_sqlite_functions(connection)


__all__ = ["register_regexp"]

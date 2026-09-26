from __future__ import annotations

import re
import sqlite3
from typing import Any


def _regexp(pattern: str | None, value: str | None) -> bool:
    # SQLite may evaluate a REGEXP branch even when a neighboring typeof()
    # predicate is false. Treat non-text source values as a non-match so
    # mixed-storage tables cannot raise Python TypeError.
    if not isinstance(pattern, str) or not isinstance(value, str):
        return False
    flags = 0
    if pattern.startswith("(?i)"):
        flags |= re.IGNORECASE
        pattern = pattern[4:]
    return re.search(pattern, value, flags) is not None


def _char_length(value: Any) -> int | None:
    """Use Python's Unicode code-point count, including text after U+0000."""
    return len(value) if isinstance(value, str) else None


def register_sqlite_functions(connection: sqlite3.Connection) -> None:
    """Register SQLRules functions needed by SQLite rules on this connection.

    SQLite does not provide REGEXP, and its built-in length(TEXT) stops at the
    first U+0000. SQLRules uses these callbacks for regex/text coercion and
    exact Python-compatible string length constraints.
    """
    connection.create_function("REGEXP", 2, _regexp)
    connection.create_function("sqlrules_char_length", 1, _char_length)

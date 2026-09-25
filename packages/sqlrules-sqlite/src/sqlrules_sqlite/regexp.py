from __future__ import annotations

import re
import sqlite3


def register_regexp(connection: sqlite3.Connection) -> None:
    """Register a flag-aware ``REGEXP`` function on a SQLite connection.

    The SQLRules SQLite ``pattern`` translator emits
    ``column REGEXP pattern``. SQLite does not ship REGEXP by default;
    call this once per connection before executing compiled SQL.

    The helper interprets an optional ``(?i)`` prefix (inserted by the
    pattern translator for case-insensitive ``PatternSpec`` values).

    Invalid patterns raise ``re.error`` (surfaced by SQLite as an
    operational error) instead of silently matching nothing.
    """

    def regexp(pattern: str | None, value: str | None) -> bool:
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

    connection.create_function("REGEXP", 2, regexp)

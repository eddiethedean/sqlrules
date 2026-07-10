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
    """

    def regexp(pattern: str | None, value: str | None) -> bool:
        if pattern is None or value is None:
            return False
        flags = 0
        if pattern.startswith("(?i)"):
            flags |= re.IGNORECASE
            pattern = pattern[4:]
        try:
            return re.search(pattern, value, flags) is not None
        except re.error:
            return False

    connection.create_function("REGEXP", 2, regexp)

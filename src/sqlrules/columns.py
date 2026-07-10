from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import MissingColumnError


def resolve_column(
    field_name: str,
    table: Any,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
    *,
    alias: str | None = None,
) -> ColumnElement[Any]:
    candidates = [field_name]
    if alias and alias not in candidates:
        candidates.append(alias)

    if column_map:
        for candidate in candidates:
            if candidate in column_map:
                return column_map[candidate]

    columns = getattr(table, "c", None)
    if columns is not None:
        for candidate in candidates:
            if candidate in columns:
                return cast(ColumnElement[Any], columns[candidate])

    # ORM mapped classes often expose columns as attributes.
    for candidate in candidates:
        attr = getattr(table, candidate, None)
        if attr is not None:
            return cast(ColumnElement[Any], attr)

    raise MissingColumnError(field=field_name)

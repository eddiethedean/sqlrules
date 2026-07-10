from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import MissingColumnError


def resolve_column(
    field_name: str,
    table: Any,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
) -> ColumnElement[Any]:
    if column_map and field_name in column_map:
        return column_map[field_name]

    columns = getattr(table, "c", None)
    if columns is not None and field_name in columns:
        return cast(ColumnElement[Any], columns[field_name])

    # ORM mapped classes often expose columns as attributes.
    candidate = getattr(table, field_name, None)
    if candidate is not None:
        return cast(ColumnElement[Any], candidate)

    raise MissingColumnError(field=field_name)

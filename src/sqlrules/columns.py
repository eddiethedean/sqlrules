from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import MissingColumnError


def _as_column_element(value: Any) -> ColumnElement[Any] | None:
    """Return a ColumnElement if *value* is (or unwraps to) one."""
    if isinstance(value, ColumnElement):
        return value
    clause_element = getattr(value, "__clause_element__", None)
    if callable(clause_element):
        try:
            unwrapped = clause_element()
        except Exception:  # pragma: no cover - defensive
            return None
        if isinstance(unwrapped, ColumnElement):
            return unwrapped
    return None


def _candidates(field_name: str, aliases: Sequence[str] | None) -> list[str]:
    """Build lookup names: aliases first (when set), then the field name."""
    ordered: list[str] = []
    if aliases:
        for alias in aliases:
            if alias and alias not in ordered:
                ordered.append(alias)
    if field_name not in ordered:
        ordered.append(field_name)
    return ordered


def resolve_column(
    field_name: str,
    table: Any,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
    *,
    alias: str | None = None,
    aliases: Sequence[str] | None = None,
) -> ColumnElement[Any]:
    alias_list: list[str] = []
    if aliases:
        alias_list.extend(aliases)
    elif alias:
        alias_list.append(alias)

    candidates = _candidates(field_name, alias_list)

    if column_map:
        for candidate in candidates:
            if candidate in column_map:
                column = _as_column_element(column_map[candidate])
                if column is None:
                    raise MissingColumnError(field=field_name)
                return column

    columns = getattr(table, "c", None)
    if columns is not None:
        for candidate in candidates:
            if candidate in columns:
                column = _as_column_element(columns[candidate])
                if column is not None:
                    return column

    # ORM mapped classes expose columns as attributes; only accept clause elements.
    for candidate in candidates:
        attr = getattr(table, candidate, None)
        column = _as_column_element(attr)
        if column is not None:
            return column

    raise MissingColumnError(field=field_name)

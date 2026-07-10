from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin
from uuid import UUID

from annotated_types import (
    Ge,
    GroupedMetadata,
    Gt,
    Le,
    Lt,
    MaxLen,
    MinLen,
    MultipleOf,
    Predicate,
)

from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import Constraint, FieldDescriptor

_SUPPORTED_TYPES: frozenset[type[Any]] = frozenset({bool, int, float, Decimal, str, date, datetime})
_UNSUPPORTED_TYPES: frozenset[type[Any]] = frozenset({UUID, time, timedelta})
_UNSUPPORTED_ORIGINS: frozenset[Any] = frozenset({list, dict, tuple, set, frozenset})
_VALIDATOR_TYPE_NAMES = frozenset(
    {
        "AfterValidator",
        "BeforeValidator",
        "PlainValidator",
        "WrapValidator",
        "FieldValidator",
        "Strict",
    }
)


def _unwrap_annotation(annotation: Any) -> Any:
    """Unwrap Optional/Union[..., None] to the non-None member when unique."""
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _iter_metadata(metadata: Any) -> Any:
    for item in metadata:
        if item is None:
            continue
        if isinstance(item, GroupedMetadata):
            yield from _iter_metadata(item)
        else:
            yield item


def ensure_supported_type(field: FieldDescriptor) -> None:
    """Raise when a field annotation is outside the v0.1 support matrix."""
    annotation = _unwrap_annotation(field.annotation)
    origin = get_origin(annotation)

    if origin is Literal:
        return

    if origin in _UNSUPPORTED_ORIGINS:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=getattr(origin, "__name__", str(origin)),
            value=annotation,
            suggestion=(
                "Remove the field or wait for a future SQLRules release with container support."
            ),
        )

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return

    if annotation in _SUPPORTED_TYPES:
        return

    if annotation in _UNSUPPORTED_TYPES or (
        isinstance(annotation, type) and annotation in _UNSUPPORTED_TYPES
    ):
        type_name = getattr(annotation, "__name__", str(annotation))
        raise UnsupportedConstraintError(
            field=field.name,
            operator=type_name,
            value=annotation,
            suggestion=f"Type {type_name!r} is not supported in SQLRules 0.1.",
        )

    # Unions with multiple non-None members and other unknown annotations.
    type_name = getattr(annotation, "__name__", repr(annotation))
    raise UnsupportedConstraintError(
        field=field.name,
        operator="type",
        value=annotation,
        suggestion=f"Annotation {type_name} is outside the SQLRules 0.1 type support matrix.",
    )


def _unsupported_constraints(field_name: str, item: Any) -> list[Constraint]:
    if isinstance(item, Predicate):
        return [Constraint(field_name, "predicate", item.func)]

    type_name = type(item).__name__
    if type_name in _VALIDATOR_TYPE_NAMES:
        return [
            Constraint(
                field_name,
                type_name,
                getattr(item, "func", getattr(item, "strict", item)),
            )
        ]

    data = getattr(item, "__dict__", None)
    if isinstance(data, dict) and data:
        return [
            Constraint(field_name, key, value) for key, value in data.items() if value is not None
        ]

    return [Constraint(field_name, type_name, item)]


def extract_constraints(field: FieldDescriptor) -> list[Constraint]:
    constraints: list[Constraint] = []

    for item in _iter_metadata(field.metadata):
        if isinstance(item, Gt):
            constraints.append(Constraint(field.name, "gt", item.gt))
        elif isinstance(item, Ge):
            constraints.append(Constraint(field.name, "ge", item.ge))
        elif isinstance(item, Lt):
            constraints.append(Constraint(field.name, "lt", item.lt))
        elif isinstance(item, Le):
            constraints.append(Constraint(field.name, "le", item.le))
        elif isinstance(item, MultipleOf):
            constraints.append(Constraint(field.name, "multiple_of", item.multiple_of))
        elif isinstance(item, MinLen):
            constraints.append(Constraint(field.name, "min_length", item.min_length))
        elif isinstance(item, MaxLen):
            constraints.append(Constraint(field.name, "max_length", item.max_length))
        else:
            constraints.extend(_unsupported_constraints(field.name, item))

    annotation = _unwrap_annotation(field.annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        constraints.append(Constraint(field.name, "literal", args))

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        values = tuple(member.value for member in annotation)
        constraints.append(Constraint(field.name, "enum", values))

    return constraints

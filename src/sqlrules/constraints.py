from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin
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
from pydantic.fields import FieldInfo

from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import Constraint, FieldDescriptor, PatternSpec, TypeSpec
from sqlrules.markers import ConstraintMarker

_SUPPORTED_TYPES: frozenset[type[Any]] = frozenset(
    {bool, int, float, Decimal, str, date, datetime, time, UUID}
)
_SUPPORTED_CONTAINER_ORIGINS: frozenset[Any] = frozenset({list, dict})
_UNSUPPORTED_TYPES: frozenset[type[Any]] = frozenset({timedelta})
_UNSUPPORTED_ORIGINS: frozenset[Any] = frozenset({tuple, set, frozenset})
_LENGTH_OPERATORS: frozenset[str] = frozenset({"min_length", "max_length"})
_NUMERIC_OPERATORS: frozenset[str] = frozenset({"gt", "ge", "lt", "le", "multiple_of"})
_PORTABLE_OPERATORS: frozenset[str] = _LENGTH_OPERATORS | _NUMERIC_OPERATORS | {"pattern"}
_TEMPORAL_TYPES: frozenset[type[Any]] = frozenset({date, datetime, time})
_VALIDATOR_TYPE_NAMES = frozenset(
    {
        "AfterValidator",
        "BeforeValidator",
        "PlainValidator",
        "WrapValidator",
        "FieldValidator",
    }
)
# Keys that map to IR constraint operators.
_CONSTRAINT_KEYS: frozenset[str] = frozenset(
    {
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_length",
        "max_length",
        "pattern",
    }
)
# Known Field keys that are intentionally unsupported (reject at extract).
_UNSUPPORTED_CONSTRAINT_KEYS: frozenset[str] = frozenset(
    {
        "max_digits",
        "decimal_places",
    }
)
# Pydantic / StringConstraints flags that are validation-only (not SQL operators).
_IGNORED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "strip_whitespace",
        "to_upper",
        "to_lower",
        "strict",
        "allow_inf_nan",
        "ascii_only",
        "coerce_numbers_to_str",
    }
)


def _unwrap_annotation(annotation: Any) -> tuple[Any, tuple[Any, ...]]:
    """Unwrap Optional/Union[..., None] and Annotated layers.

    Returns the concrete annotation and any metadata collected from Annotated
    wrappers (used when Pydantic leaves field.metadata empty for
    ``Annotated[T, ...] | None``).
    """
    collected: list[Any] = []
    current = annotation

    while True:
        origin = get_origin(current)
        if origin is Annotated:
            args = get_args(current)
            if not args:
                break
            current = args[0]
            collected.extend(args[1:])
            continue
        if origin is Union or origin is UnionType:
            non_none = [arg for arg in get_args(current) if arg is not type(None)]
            if len(non_none) == 1:
                current = non_none[0]
                continue
        break

    return current, tuple(collected)


def _iter_metadata(metadata: Any) -> Any:
    for item in metadata:
        if item is None:
            continue
        if isinstance(item, GroupedMetadata):
            yield from _iter_metadata(item)
        elif isinstance(item, FieldInfo):
            # Annotated[..., Field(...)] | None leaves FieldInfo in the annotation
            # metadata when field.metadata is empty.
            yield from _iter_metadata(item.metadata)
        else:
            yield item


def _field_metadata(field: FieldDescriptor) -> tuple[Any, ...]:
    if field.metadata:
        return field.metadata
    _, annotated_metadata = _unwrap_annotation(field.annotation)
    return annotated_metadata


def _concrete_type(field: FieldDescriptor) -> Any:
    annotation, _ = _unwrap_annotation(field.annotation)
    return annotation


def _annotation_allows_none(annotation: Any) -> bool:
    """Return True when the raw annotation admits ``None`` (Optional / ``T | None``)."""
    current = annotation
    while True:
        origin = get_origin(current)
        if origin is Annotated:
            args = get_args(current)
            if not args:
                return False
            current = args[0]
            continue
        if origin is Union or origin is UnionType:
            return any(arg is type(None) for arg in get_args(current))
        return False


def _is_strict_marker(item: Any) -> bool:
    if isinstance(item, type):
        return False
    return type(item).__name__ == "Strict" and hasattr(item, "strict")


def resolve_field_strict(field: FieldDescriptor, *, model_strict: bool = False) -> bool:
    """Resolve Pydantic strictness: field ``Strict`` / ``strict=`` then model config."""
    for item in _iter_metadata(_field_metadata(field)):
        if _is_strict_marker(item):
            return bool(item.strict)
        data = getattr(item, "__dict__", None)
        if isinstance(data, dict) and "strict" in data and data["strict"] is not None:
            # e.g. StringConstraints(strict=True, ...) when not already a Strict marker
            return bool(data["strict"])
    return model_strict


def _is_container_type(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin in _SUPPORTED_CONTAINER_ORIGINS:
        return True
    return annotation in _SUPPORTED_CONTAINER_ORIGINS


def ensure_supported_type(field: FieldDescriptor) -> None:
    """Raise when a field annotation is outside the support matrix."""
    annotation = _concrete_type(field)
    origin = get_origin(annotation)

    if origin is Literal:
        return

    if origin in _UNSUPPORTED_ORIGINS or annotation in _UNSUPPORTED_ORIGINS:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=getattr(origin or annotation, "__name__", str(origin or annotation)),
            value=annotation,
            suggestion=(
                "Remove the field or wait for a future SQLRules release with "
                f"{getattr(origin or annotation, '__name__', origin or annotation)!r} support."
            ),
        )

    if _is_container_type(annotation):
        return

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
            suggestion=f"Type {type_name!r} is not supported by SQLRules.",
        )

    # Unions with multiple non-None members and other unknown annotations.
    type_name = getattr(annotation, "__name__", repr(annotation))
    raise UnsupportedConstraintError(
        field=field.name,
        operator="type",
        value=annotation,
        suggestion=f"Annotation {type_name} is outside the SQLRules type support matrix.",
    )


def _normalize_pattern(field_name: str, pattern: Any) -> PatternSpec:
    if isinstance(pattern, PatternSpec):
        return pattern
    if isinstance(pattern, str):
        return PatternSpec(pattern=pattern, ignore_case=False)
    if isinstance(pattern, re.Pattern):
        return PatternSpec(
            pattern=str(pattern.pattern),
            ignore_case=bool(pattern.flags & re.IGNORECASE),
        )
    raise UnsupportedConstraintError(
        field=field_name,
        operator="pattern",
        value=pattern,
        suggestion="pattern must be a str or re.Pattern.",
    )


def pattern_text(value: Any) -> tuple[str, bool]:
    """Return ``(pattern, ignore_case)`` from a ``pattern`` constraint value."""
    if isinstance(value, PatternSpec):
        return value.pattern, value.ignore_case
    if isinstance(value, str):
        return value, False
    raise TypeError(f"pattern value must be str or PatternSpec, got {type(value)!r}")


def type_spec(value: Any) -> TypeSpec:
    """Return a ``TypeSpec`` from a ``type_check`` constraint value."""
    if isinstance(value, TypeSpec):
        return value
    raise TypeError(f"type_check value must be TypeSpec, got {type(value)!r}")


def _constraints_from_mapping(field_name: str, data: dict[str, Any]) -> list[Constraint]:
    """Map whitelisted metadata keys into IR; ignore validation-only flags."""
    constraints: list[Constraint] = []
    for key, value in data.items():
        if value is None or key in _IGNORED_METADATA_KEYS:
            continue
        if key in _UNSUPPORTED_CONSTRAINT_KEYS:
            raise UnsupportedConstraintError(
                field=field_name,
                operator=key,
                value=value,
                suggestion=(
                    f"{key!r} is not supported by SQLRules 1.0 "
                    "(no portable SQL mapping). Remove it or wait for a future release."
                ),
            )
        if key == "pattern":
            constraints.append(
                Constraint(field_name, "pattern", _normalize_pattern(field_name, value))
            )
        elif key in _CONSTRAINT_KEYS:
            constraints.append(Constraint(field_name, key, value))
        else:
            raise UnsupportedConstraintError(
                field=field_name,
                operator=key,
                value=value,
                suggestion=(
                    f"Unknown metadata key {key!r} is not a SQLRules constraint. "
                    "Use Field constraints, annotated-types, or sqlrules.markers."
                ),
            )
    return constraints


def _is_constraint_marker(item: Any) -> bool:
    if isinstance(item, type):
        return False
    return isinstance(item, ConstraintMarker)


def _unsupported_constraints(field_name: str, item: Any) -> list[Constraint]:
    if _is_constraint_marker(item):
        return [Constraint(field_name, item.operator, item.value)]

    if _is_strict_marker(item):
        # Strictness is resolved separately for type_check; not an SQL operator.
        return []

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

    # First-class pattern attribute (e.g. _PydanticGeneralMetadata(pattern=...)).
    pattern = getattr(item, "pattern", None)
    if pattern is not None and isinstance(pattern, (str, re.Pattern, PatternSpec)):
        constraints = _constraints_from_mapping(
            field_name,
            {
                key: value
                for key, value in getattr(item, "__dict__", {}).items()
                if key != "pattern" and value is not None
            },
        )
        constraints.append(
            Constraint(field_name, "pattern", _normalize_pattern(field_name, pattern))
        )
        return constraints

    data = getattr(item, "__dict__", None)
    if isinstance(data, dict) and data:
        return _constraints_from_mapping(field_name, data)

    return [Constraint(field_name, type_name, item)]


def _should_emit_type_check(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Literal:
        return False
    if _is_container_type(annotation):
        return False
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return False
    return annotation in _SUPPORTED_TYPES


def _reject_type_operator_mismatch(field: FieldDescriptor, constraint: Constraint) -> None:
    annotation = _concrete_type(field)
    origin = get_origin(annotation)

    if _is_container_type(annotation) and constraint.operator in _PORTABLE_OPERATORS:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion=(
                "Portable constraints are not valid on list/dict fields; "
                "use sqlrules.markers (e.g. JsonContains, ArrayContains) instead."
            ),
        )

    if origin is Literal:
        if (
            constraint.operator not in {"literal", "enum"}
            and constraint.operator in _LENGTH_OPERATORS | _NUMERIC_OPERATORS
        ):
            raise UnsupportedConstraintError(
                field=field.name,
                operator=constraint.operator,
                value=constraint.value,
                suggestion=(f"Constraint {constraint.operator!r} is not valid for Literal fields."),
            )
        return

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        if constraint.operator in _LENGTH_OPERATORS | _NUMERIC_OPERATORS:
            raise UnsupportedConstraintError(
                field=field.name,
                operator=constraint.operator,
                value=constraint.value,
                suggestion=f"Constraint {constraint.operator!r} is not valid for Enum fields.",
            )
        return

    if annotation is bool and constraint.operator in _LENGTH_OPERATORS | _NUMERIC_OPERATORS:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion=("Bool fields only support Literal/equality-style constraints in SQLRules."),
        )

    if annotation is UUID and constraint.operator in _LENGTH_OPERATORS | _NUMERIC_OPERATORS:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion=("UUID fields only support Literal/Enum-style constraints in SQLRules."),
        )

    if annotation in _TEMPORAL_TYPES and constraint.operator == "multiple_of":
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion=(
                "multiple_of is not valid for date/datetime/time fields; "
                "use gt/ge/lt/le range constraints."
            ),
        )

    if constraint.operator in _LENGTH_OPERATORS and annotation is not str:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion="Length constraints require a str field annotation.",
        )

    if constraint.operator in _NUMERIC_OPERATORS and annotation is str:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion="Numeric comparison constraints are not valid for str fields.",
        )

    if constraint.operator == "pattern" and annotation is not str:
        raise UnsupportedConstraintError(
            field=field.name,
            operator=constraint.operator,
            value=constraint.value,
            suggestion="pattern constraints require a str field annotation.",
        )


def extract_constraints(
    field: FieldDescriptor,
    *,
    emit_type_checks: bool = False,
    model_strict: bool = False,
) -> list[Constraint]:
    constraints: list[Constraint] = []

    for item in _iter_metadata(_field_metadata(field)):
        if _is_constraint_marker(item):
            constraints.append(Constraint(field.name, item.operator, item.value))
        elif isinstance(item, Gt):
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

    annotation = _concrete_type(field)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        constraints.append(Constraint(field.name, "literal", args))

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        values = tuple(member.value for member in annotation)
        constraints.append(Constraint(field.name, "enum", values))

    if emit_type_checks and _should_emit_type_check(annotation):
        strict = resolve_field_strict(field, model_strict=model_strict)
        constraints.append(
            Constraint(
                field.name,
                "type_check",
                TypeSpec(
                    python_type=annotation,
                    strict=strict,
                    allow_none=_annotation_allows_none(field.annotation),
                ),
            )
        )

    for constraint in constraints:
        if constraint.operator in _PORTABLE_OPERATORS:
            _reject_type_operator_mismatch(field, constraint)

    return constraints

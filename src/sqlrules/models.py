from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin
from uuid import UUID

from annotated_types import Ge, Gt, Interval, Le, Lt, MaxLen, MinLen, MultipleOf
from pydantic import BaseModel, ConfigDict
from pydantic import Field as _PydanticField
from pydantic_core import PydanticUndefined

from sqlrules.errors import InvalidModelError, UnsupportedConstraintError
from sqlrules.ir import Constraint, FieldDescriptor, RuleField, SchemaSpec
from sqlrules.markers import ConstraintMarker


@dataclass(frozen=True, slots=True)
class RuleConfig:
    """SQLRules-only model options, separate from Pydantic's ``model_config``."""

    allow_empty: bool = False


@dataclass(frozen=True, slots=True)
class ColumnBinding:
    """Explicit database column name attached by :func:`Field`."""

    name: str


def Field(default: Any = PydanticUndefined, *, column: str | None = None, **kwargs: Any) -> Any:
    """Pydantic ``Field`` with optional SQLRules database-column metadata.

    All standard Pydantic field options retain their normal model behavior.
    ``column`` is the only SQLRules-specific option and never changes a
    Pydantic alias or serialized field name.
    """
    if column is not None and (not isinstance(column, str) or not column):
        raise TypeError("column must be a non-empty string")
    if default is PydanticUndefined:
        result = _PydanticField(**kwargs)
    else:
        result = _PydanticField(default, **kwargs)
    if column is not None:
        result.metadata.append(ColumnBinding(column))
    return result


_SCALAR_TYPES = frozenset({bool, int, float, Decimal, str, date, datetime, time, UUID})
_KNOWN_CONSTRAINT_METADATA = (Gt, Ge, Lt, Le, MultipleOf, MinLen, MaxLen, Interval)
_RULE_OPERATORS = frozenset(
    {
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_length",
        "max_length",
        "pattern",
        "literal",
        "enum",
        "json_contains",
        "json_has_key",
        "array_contains",
        "array_overlap",
        "range_contains",
        "range_overlap",
        "fulltext_match",
    }
)


def _unwrap(annotation: Any) -> tuple[Any, bool, tuple[Any, ...]]:
    nullable = False
    metadata: list[Any] = []
    current = annotation
    while True:
        origin = get_origin(current)
        if origin is Annotated:
            args = get_args(current)
            if not args:
                break
            current = args[0]
            metadata.extend(args[1:])
            continue
        if origin in (Union, UnionType):
            args = get_args(current)
            members = [item for item in args if item is not type(None)]
            nullable = nullable or len(members) != len(args)
            if len(members) == 1:
                current = members[0]
                continue
        break
    return current, nullable, tuple(metadata)


def _metadata_values(field: Any, annotation_metadata: tuple[Any, ...]) -> tuple[Any, ...]:
    values = list(getattr(field, "metadata", ()) or ())
    for item in annotation_metadata:
        if item not in values:
            values.append(item)
    return tuple(values)


def _is_strict_metadata(item: Any) -> bool:
    return type(item).__name__ == "Strict" and hasattr(item, "strict")


def _recognized_metadata(item: Any) -> bool:
    if isinstance(item, (ColumnBinding, ConstraintMarker, *_KNOWN_CONSTRAINT_METADATA)):
        return True
    if _is_strict_metadata(item):
        return True
    if type(item).__name__ == "StringConstraints":
        allowed = {"min_length", "max_length", "pattern", "strict"}
        return all(value is None for key, value in vars(item).items() if key not in allowed)
    if type(item).__name__ in {"PydanticGeneralMetadata", "_PydanticGeneralMetadata"}:
        allowed = {"pattern", "strict"}
        return all(value is None for key, value in vars(item).items() if key not in allowed)
    return False


def _domain_type(annotation: Any, field_name: str) -> Any:
    origin = get_origin(annotation)
    if origin is Literal:
        values = get_args(annotation)
        if not values:
            raise UnsupportedConstraintError(field_name, "literal", values)
        types = {type(value.value if isinstance(value, Enum) else value) for value in values}
        if len(types) != 1 or next(iter(types)) not in _SCALAR_TYPES:
            raise UnsupportedConstraintError(
                field_name,
                "literal",
                values,
                "Literal values must use one supported scalar type.",
            )
        return next(iter(types))
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        enum_values = tuple(member.value for member in annotation)
        types = {type(value) for value in enum_values}
        if not enum_values or len(types) != 1 or next(iter(types)) not in _SCALAR_TYPES:
            raise UnsupportedConstraintError(
                field_name,
                "enum",
                annotation,
                "Enum values must use one supported scalar type.",
            )
        return next(iter(types))
    origin = get_origin(annotation)
    if annotation in _SCALAR_TYPES:
        return annotation
    if origin in (list, dict):
        return origin
    if annotation in (list, dict):
        return annotation
    raise UnsupportedConstraintError(
        field_name,
        "type",
        annotation,
        "Use a supported scalar, Literal, Enum, list, or dict annotation.",
    )


def _strictness(field: Any, metadata: tuple[Any, ...], model_strict: bool) -> bool:
    explicit = getattr(field, "strict", None)
    if explicit is not None:
        return bool(explicit)
    # Pydantic stores strict aliases and Annotated Strict markers in metadata.
    for item in metadata:
        if _is_strict_metadata(item):
            return bool(item.strict)
        if type(item).__name__ == "StringConstraints" and item.strict is not None:
            return bool(item.strict)
    return model_strict


def _normalize_constraints(
    field: FieldDescriptor,
    metadata: tuple[Any, ...],
) -> tuple[Constraint, ...]:
    from sqlrules.constraints import extract_constraints

    usable = tuple(item for item in metadata if not isinstance(item, ColumnBinding))
    normalized = FieldDescriptor(
        name=field.name,
        alias=field.alias,
        annotation=field.annotation,
        metadata=usable,
        aliases=field.aliases,
    )
    constraints = extract_constraints(normalized)
    constraints = [
        Constraint(
            item.field,
            item.operator,
            tuple(value.value if isinstance(value, Enum) else value for value in item.value)
            if item.operator == "literal"
            else item.value,
        )
        for item in constraints
    ]
    seen: dict[str, Any] = {}
    for item in constraints:
        if item.operator not in _RULE_OPERATORS:
            raise UnsupportedConstraintError(
                field.name,
                item.operator,
                item.value,
                "Python validators and unrecognized metadata do not have SQL rule equivalents.",
            )
        numeric_value = isinstance(item.value, (int, float, Decimal)) and not isinstance(
            item.value, bool
        )
        finite = (
            item.value.is_finite()
            if isinstance(item.value, Decimal)
            else math.isfinite(item.value)
            if isinstance(item.value, float)
            else True
        )
        if item.operator in {"gt", "ge", "lt", "le", "multiple_of"} and (
            isinstance(item.value, (float, Decimal)) and not finite
        ):
            raise UnsupportedConstraintError(
                field.name,
                item.operator,
                item.value,
                "Numeric constraints must use finite values.",
            )
        if item.operator == "multiple_of" and (not numeric_value or item.value <= 0):
            raise UnsupportedConstraintError(
                field.name,
                item.operator,
                item.value,
                "multiple_of must be a positive finite number.",
            )
        if item.operator in seen:
            raise UnsupportedConstraintError(
                field.name,
                item.operator,
                item.value,
                "Duplicate constraints are not allowed; combine them into one declaration.",
            )
        seen[item.operator] = item.value
        if item.operator in {"min_length", "max_length"} and (
            isinstance(item.value, bool) or not isinstance(item.value, int) or item.value < 0
        ):
            raise UnsupportedConstraintError(
                field.name,
                item.operator,
                item.value,
                "Length constraints must be non-negative integers.",
            )
    min_length = seen.get("min_length")
    max_length = seen.get("max_length")
    if min_length is not None and max_length is not None and min_length > max_length:
        raise UnsupportedConstraintError(
            field.name,
            "length",
            (min_length, max_length),
            "min_length cannot exceed max_length.",
        )
    lower = [(seen[key], key == "gt") for key in ("gt", "ge") if key in seen]
    upper = [(seen[key], key == "lt") for key in ("lt", "le") if key in seen]
    if lower and upper:
        strongest_lower = max(value for value, _ in lower)
        strongest_upper = min(value for value, _ in upper)
        lower_exclusive = any(value == strongest_lower and exclusive for value, exclusive in lower)
        upper_exclusive = any(value == strongest_upper and exclusive for value, exclusive in upper)
        if strongest_lower > strongest_upper or (
            strongest_lower == strongest_upper and (lower_exclusive or upper_exclusive)
        ):
            raise UnsupportedConstraintError(
                field.name,
                "bounds",
                (tuple(lower), tuple(upper)),
                "The declared lower and upper bounds cannot both be satisfied.",
            )
    return tuple(constraints)


def normalize_schema(model: type[BaseModel]) -> SchemaSpec:
    """Normalize one ``RuleSchema`` class into immutable SQLRules fields."""
    if not isinstance(model, type) or not issubclass(model, RuleSchema):
        raise InvalidModelError(model=model)
    if model is RuleSchema:
        raise InvalidModelError(model=model)

    rule_bases = [
        base
        for base in model.__bases__
        if isinstance(base, type) and issubclass(base, RuleSchema) and base is not RuleSchema
    ]
    if len(rule_bases) > 1:
        raise UnsupportedConstraintError(
            model.__name__,
            "multiple_inheritance",
            tuple(base.__name__ for base in rule_bases),
            "RuleSchema supports single inheritance only.",
        )

    decorators = getattr(model, "__pydantic_decorators__", None)
    if decorators is not None:
        for name in (
            "field_validators",
            "model_validators",
            "field_serializers",
            "model_serializers",
        ):
            if getattr(decorators, name, None):
                raise UnsupportedConstraintError(
                    model.__name__,
                    name,
                    None,
                    "Custom Python validators and serializers cannot be compiled as SQL rules.",
                )
        if getattr(decorators, "computed_fields", None):
            raise UnsupportedConstraintError(
                model.__name__,
                "computed_field",
                None,
                "Computed fields do not have a bound database source column.",
            )
    if getattr(model, "__pydantic_custom_init__", False):
        raise UnsupportedConstraintError(
            model.__name__,
            "custom_init",
            None,
            "A custom __init__ has no equivalent SQL rule semantics.",
        )
    if getattr(model, "__pydantic_post_init__", None):
        raise UnsupportedConstraintError(
            model.__name__,
            "model_post_init",
            None,
            "A custom model_post_init callback has no equivalent SQL rule semantics.",
        )
    for hook in ("__get_pydantic_core_schema__", "__get_pydantic_json_schema__"):
        if any(hook in base.__dict__ for base in model.__mro__ if base is not BaseModel):
            raise UnsupportedConstraintError(
                model.__name__,
                hook,
                None,
                "Custom Pydantic schema hooks are outside the SQLRules declaration subset.",
            )

    rule_config = getattr(model, "__rule_config__", RuleConfig())
    if not isinstance(rule_config, RuleConfig):
        raise TypeError("__rule_config__ must be a RuleConfig instance")
    model_strict = bool(model.model_config.get("strict", False))
    incompatible_config = {
        key: model.model_config.get(key)
        for key in (
            "coerce_numbers_to_str",
            "str_strip_whitespace",
            "str_to_lower",
            "str_to_upper",
            "str_min_length",
            "str_max_length",
        )
        if model.model_config.get(key) not in (None, False)
    }
    if incompatible_config:
        raise UnsupportedConstraintError(
            model.__name__,
            "model_config",
            incompatible_config,
            "String coercion, normalization, and global length settings are "
            "outside the SQLRules 2.0 declaration subset.",
        )

    fields: list[RuleField] = []
    provenance = getattr(model, "__sqlrules_provenance__", "native")
    for name, info in model.model_fields.items():
        annotation = info.annotation
        concrete, nullable, annotated_metadata = _unwrap(annotation)
        metadata = _metadata_values(info, annotated_metadata)
        unknown = [item for item in metadata if not _recognized_metadata(item)]
        if unknown:
            raise UnsupportedConstraintError(
                name,
                "metadata",
                unknown[0],
                "Only SQLRules constraints and supported Pydantic constraint metadata are allowed.",
            )

        field_descriptor = FieldDescriptor(
            name=name,
            alias=info.alias if isinstance(info.alias, str) else None,
            annotation=annotation,
            metadata=metadata,
            aliases=tuple(
                alias
                for alias in (info.alias, info.validation_alias, info.serialization_alias)
                if isinstance(alias, str)
            ),
        )
        python_type = _domain_type(concrete, name)
        constraints = _normalize_constraints(
            field_descriptor,
            metadata,
        )
        strict = _strictness(info, metadata, model_strict)
        binding = next((item.name for item in metadata if isinstance(item, ColumnBinding)), None)
        if python_type in {list, dict}:
            operators = {item.operator for item in constraints}
            json_markers = {"json_contains", "json_has_key"}
            array_markers = {"array_contains", "array_overlap"}
            if python_type is list and operators & json_markers:
                python_type = dict
            elif python_type is dict and operators & array_markers:
                raise UnsupportedConstraintError(
                    name,
                    "array_marker",
                    annotation,
                    "Array markers require a list field; JSON markers require a dict field.",
                )
            elif not (operators & (json_markers | array_markers)):
                raise UnsupportedConstraintError(
                    name,
                    "type",
                    annotation,
                    "Container fields require a compatible JSON or array marker.",
                )

        for item in constraints:
            if item.operator in {"min_length", "max_length", "pattern"} and python_type is not str:
                raise UnsupportedConstraintError(name, item.operator, item.value)
            if item.operator in {"gt", "ge", "lt", "le", "multiple_of"} and python_type in {
                bool,
                str,
                UUID,
                list,
                dict,
            }:
                raise UnsupportedConstraintError(name, item.operator, item.value)

        examples = getattr(info, "examples", None) or ()
        fields.append(
            RuleField(
                name=name,
                annotation=annotation,
                python_type=python_type,
                nullable=nullable,
                strict=strict,
                constraints=constraints,
                column=binding,
                alias=info.alias if isinstance(info.alias, str) else None,
                title=info.title,
                description=info.description,
                examples=tuple(examples),
                source=provenance,
                source_location=f"{model.__module__}.{model.__qualname__}.{name}",
            )
        )

    if not fields and not rule_config.allow_empty:
        raise UnsupportedConstraintError(
            model.__name__,
            "empty_schema",
            None,
            "Use __rule_config__ = RuleConfig(allow_empty=True) to allow an always-true predicate.",
        )
    return SchemaSpec(
        model=model,
        fields=tuple(fields),
        allow_empty=rule_config.allow_empty,
        provenance=provenance,
    )


class RuleSchema(BaseModel):
    """Pydantic model whose field declarations are restricted to SQLRules rules."""

    model_config = ConfigDict()
    __rule_config__: ClassVar[RuleConfig] = RuleConfig()
    __sqlrules_provenance__: ClassVar[str] = "native"

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        try:
            normalize_schema(cls)
        except (InvalidModelError, UnsupportedConstraintError, TypeError, ValueError) as exc:
            raise TypeError(f"Invalid SQLRules RuleSchema {cls.__name__}: {exc}") from exc


__all__ = ["ColumnBinding", "Field", "RuleConfig", "RuleSchema", "normalize_schema"]

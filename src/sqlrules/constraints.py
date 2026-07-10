from __future__ import annotations

from enum import Enum
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from annotated_types import Ge, Gt, Le, Len, Lt, MaxLen, MinLen, MultipleOf

from sqlrules.ir import Constraint, FieldDescriptor


def _unwrap_annotation(annotation: Any) -> Any:
    """Unwrap Optional/Union[..., None] to the non-None member when unique."""
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def extract_constraints(field: FieldDescriptor) -> list[Constraint]:
    constraints: list[Constraint] = []

    for item in field.metadata:
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
        elif isinstance(item, Len):
            constraints.append(Constraint(field.name, "min_length", item.min_length))
            if item.max_length is not None:
                constraints.append(Constraint(field.name, "max_length", item.max_length))

    annotation = _unwrap_annotation(field.annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        constraints.append(Constraint(field.name, "literal", args))

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        values = tuple(member.value for member in annotation)
        constraints.append(Constraint(field.name, "enum", values))

    return constraints

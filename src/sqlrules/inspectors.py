from __future__ import annotations

from pydantic import BaseModel

from sqlrules.errors import InvalidModelError
from sqlrules.ir import FieldDescriptor


def inspect_model(model: type[BaseModel]) -> list[FieldDescriptor]:
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise InvalidModelError(model=model)

    descriptors: list[FieldDescriptor] = []
    for name, field in model.model_fields.items():
        descriptors.append(
            FieldDescriptor(
                name=name,
                alias=field.alias,
                annotation=field.annotation,
                metadata=tuple(field.metadata),
            )
        )
    return descriptors

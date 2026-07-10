from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, AliasPath, BaseModel

from sqlrules.errors import InvalidModelError
from sqlrules.ir import FieldDescriptor


def _string_alias(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _field_aliases(field: Any) -> tuple[str | None, tuple[str, ...]]:
    """Return primary alias and extra string alias candidates for column binding."""
    aliases: list[str] = []

    primary = _string_alias(field.alias)
    if primary:
        aliases.append(primary)

    for attr in ("validation_alias", "serialization_alias"):
        value = getattr(field, attr, None)
        # AliasPath / AliasChoices are not used for column binding.
        if isinstance(value, (AliasPath, AliasChoices)):
            continue
        candidate = _string_alias(value)
        if candidate and candidate not in aliases:
            aliases.append(candidate)

    primary_alias = aliases[0] if aliases else None
    return primary_alias, tuple(aliases)


def inspect_model(model: type[BaseModel]) -> list[FieldDescriptor]:
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise InvalidModelError(model=model)

    descriptors: list[FieldDescriptor] = []
    for name, field in model.model_fields.items():
        primary_alias, aliases = _field_aliases(field)
        descriptors.append(
            FieldDescriptor(
                name=name,
                alias=primary_alias,
                aliases=aliases,
                annotation=field.annotation,
                metadata=tuple(field.metadata),
            )
        )
    return descriptors

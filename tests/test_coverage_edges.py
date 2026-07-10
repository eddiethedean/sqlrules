import operator
from enum import Enum
from typing import Annotated

import pytest
from annotated_types import Len
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import sqlrules
from sqlrules.translators import TranslatorRegistry, _binary


def test_column_map_override() -> None:
    class Filter(BaseModel):
        user_age: Annotated[int, Field(ge=18)]

    table = Table("users", MetaData(), Column("age", Integer))
    rules = sqlrules.compile(
        Filter,
        table,
        column_map={"user_age": table.c.age},
    )
    assert "user_age" in rules
    assert len(rules["user_age"]) == 1


def test_orm_attribute_resolution() -> None:
    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        age: Mapped[int] = mapped_column(Integer)

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=21)]

    rules = sqlrules.compile(Filter, User)
    assert "age" in rules


def test_len_constraint() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Len(2, 10)]

    table = Table("users", MetaData(), Column("name", String))
    rules = sqlrules.compile(Filter, table)
    assert len(rules["name"]) == 2


def test_duplicate_registry_registration() -> None:
    registry = TranslatorRegistry()
    registry.register("gt", _binary(operator.gt))
    try:
        registry.register("gt", _binary(operator.gt))
        raise AssertionError("expected RegistryError")
    except sqlrules.RegistryError:
        pass


def test_exception_messages_from_compile() -> None:
    table = Table("users", MetaData(), Column("id", Integer))

    class Missing(BaseModel):
        age: Annotated[int, Field(ge=18)]

    with pytest.raises(sqlrules.MissingColumnError) as missing:
        sqlrules.compile(Missing, table)
    assert "age" in str(missing.value)

    class Pattern(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    name_table = Table("users", MetaData(), Column("name", String))
    with pytest.raises(sqlrules.UnsupportedConstraintError) as unsupported:
        sqlrules.compile(Pattern, name_table)
    assert "pattern" in str(unsupported.value)
    assert unsupported.value.suggestion is not None
    assert "on_unsupported" in unsupported.value.suggestion

    with pytest.raises(sqlrules.InvalidModelError) as invalid:
        sqlrules.compile(object, table)  # type: ignore[arg-type]
    assert "BaseModel" in str(invalid.value)


def test_translator_error_wraps_unexpected_failure() -> None:
    from sqlrules.translators import default_registry

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    table = Table("users", MetaData(), Column("age", Integer))
    registry = default_registry().copy()

    def boom(constraint, column, context):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    registry.register_constraint("ge", boom, on_conflict="replace")
    with pytest.raises(sqlrules.TranslatorError, match="boom") as err:
        sqlrules.Compiler(registry=registry, cache=False).compile(Filter, table)
    assert err.value.field == "age"
    assert err.value.operator == "ge"


def test_enum_values() -> None:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    class Filter(BaseModel):
        color: Color

    table = Table("items", MetaData(), Column("color", String))
    rules = sqlrules.compile(Filter, table)
    assert "color" in rules

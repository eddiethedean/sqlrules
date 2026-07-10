import operator
from enum import Enum
from typing import Annotated

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


def test_exception_messages() -> None:
    assert "BaseModel" in str(sqlrules.InvalidModelError(model=int))
    assert "age" in str(sqlrules.MissingColumnError(field="age"))
    assert "pattern" in str(sqlrules.UnsupportedConstraintError(field="name", operator="pattern"))
    assert "failed" in str(sqlrules.TranslatorError(field="age", operator="ge", message="boom"))
    assert "gt" in str(sqlrules.InvalidTranslatorError(operator="gt", translator=None))
    assert "dup" in str(sqlrules.RegistryError(message="dup"))
    assert "on_unsupported" in str(
        sqlrules.ConfigurationError(option="on_unsupported", value="nope")
    )


def test_enum_values() -> None:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    class Filter(BaseModel):
        color: Color

    table = Table("items", MetaData(), Column("color", String))
    rules = sqlrules.compile(Filter, table)
    assert "color" in rules

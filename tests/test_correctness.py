from datetime import time, timedelta
from enum import Enum
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.sql.elements import ColumnElement

import sqlrules
from sqlrules import MissingColumnError, UnsupportedConstraintError


def test_table_name_attribute_collision_raises() -> None:
    """Field 'name' must not bind to Table.name (the table's string name)."""
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        name: Annotated[str, Field(min_length=1)]

    with pytest.raises(MissingColumnError, match="name"):
        sqlrules.compile(Filter, table)


def test_table_bool_attribute_collision_raises() -> None:
    """Field matching a Table bool attribute must not emit Python bools."""
    table = Table("users", MetaData(), Column("id", Integer))

    class Filter(BaseModel):
        is_selectable: Annotated[int, Field(ge=1)]

    with pytest.raises(MissingColumnError, match="is_selectable"):
        sqlrules.compile(Filter, table)


def test_optional_annotated_unwraps_metadata() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)] | None = None

    rules = sqlrules.compile(Filter, table)
    assert "age" in rules
    assert len(rules["age"]) == 1
    assert isinstance(rules["age"][0], ColumnElement)


def test_validation_alias_resolves_column() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        years: Annotated[int, Field(ge=18, validation_alias="age")]

    rules = sqlrules.compile(Filter, table)
    assert "years" in rules
    compiled = str(select(table).where(*sqlrules.where(rules)))
    assert "age" in compiled


def test_serialization_alias_resolves_column() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        years: Annotated[int, Field(ge=18, serialization_alias="age")]

    rules = sqlrules.compile(Filter, table)
    assert "years" in rules


def test_alias_preferred_over_field_name_when_both_exist() -> None:
    table = Table(
        "users",
        MetaData(),
        Column("years", Integer),
        Column("user_age", Integer),
    )

    class Filter(BaseModel):
        years: Annotated[int, Field(ge=18, alias="user_age")]

    rules = sqlrules.compile(Filter, table)
    compiled = str(select(table).where(*sqlrules.where(rules)))
    assert "user_age" in compiled
    assert "years" not in compiled.split("WHERE", 1)[1]


def test_unconstrained_orphan_field_skipped() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        orphan: str
        age: Annotated[int, Field(ge=18)]

    rules = sqlrules.compile(Filter, table)
    assert list(rules) == ["age"]


def test_multiple_of_zero_rejected() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(multiple_of=0)]

    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        sqlrules.compile(Filter, table)


def test_multiple_of_negative_rejected() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(multiple_of=-2)]

    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        sqlrules.compile(Filter, table)


def test_on_unsupported_ignore_still_raises_for_timedelta() -> None:
    table = Table("users", MetaData(), Column("delta", String))

    class Filter(BaseModel):
        delta: timedelta

    with pytest.raises(UnsupportedConstraintError, match="timedelta"):
        sqlrules.compile(Filter, table, on_unsupported="ignore")


def test_on_unsupported_ignore_still_raises_for_unsupported_containers() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: set[int]

    with pytest.raises(UnsupportedConstraintError, match="set"):
        sqlrules.compile(Filter, table, on_unsupported="ignore")


def test_unconstrained_list_field_skipped() -> None:
    table = Table("users", MetaData(), Column("tags", String))

    class Filter(BaseModel):
        tags: list[str]

    assert sqlrules.compile(Filter, table) == {}


def test_timedelta_unsupported_time_allowed() -> None:
    table = Table(
        "users",
        MetaData(),
        Column("start", String),
        Column("delta", String),
    )

    class TimeFilter(BaseModel):
        start: time

    class DeltaFilter(BaseModel):
        delta: timedelta

    # Unconstrained time fields are skipped (type is supported in 0.2).
    assert sqlrules.compile(TimeFilter, table) == {}
    with pytest.raises(UnsupportedConstraintError, match="timedelta"):
        sqlrules.compile(DeltaFilter, table)


def test_length_constraint_on_int_rejected() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(min_length=2)]

    with pytest.raises(UnsupportedConstraintError, match="min_length"):
        sqlrules.compile(Filter, table)


def test_numeric_constraint_on_str_rejected() -> None:
    table = Table("users", MetaData(), Column("name", String))

    class Filter(BaseModel):
        name: Annotated[str, Field(ge=5)]

    with pytest.raises(UnsupportedConstraintError, match="ge"):
        sqlrules.compile(Filter, table)


def test_numeric_constraint_on_bool_rejected() -> None:
    table = Table("users", MetaData(), Column("active", Integer))

    class Filter(BaseModel):
        active: Annotated[bool, Field(ge=True)]

    with pytest.raises(UnsupportedConstraintError, match="ge"):
        sqlrules.compile(Filter, table)


def test_literal_with_numeric_constraint_rejected() -> None:
    table = Table("users", MetaData(), Column("status", String))

    class Filter(BaseModel):
        status: Annotated[Literal["ACTIVE", "DISABLED"], Field(ge=1)]

    with pytest.raises(UnsupportedConstraintError, match="ge"):
        sqlrules.compile(Filter, table)


def test_enum_with_length_constraint_rejected() -> None:
    class Status(Enum):
        ACTIVE = "ACTIVE"
        DISABLED = "DISABLED"

    table = Table("users", MetaData(), Column("status", String))

    class Filter(BaseModel):
        status: Annotated[Status, Field(min_length=1)]

    with pytest.raises(UnsupportedConstraintError, match="min_length"):
        sqlrules.compile(Filter, table)


def test_union_of_supported_types_rejected() -> None:
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: int | str

    with pytest.raises(UnsupportedConstraintError, match="type"):
        sqlrules.compile(Filter, table)


def test_alias_path_ignored_for_column_binding() -> None:
    from pydantic import AliasPath

    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        years: Annotated[int, Field(ge=18, validation_alias=AliasPath("nested", "age"))]

    with pytest.raises(MissingColumnError, match="years"):
        sqlrules.compile(Filter, table)


def test_column_map_skips_non_column_values() -> None:
    table = Table("users", MetaData(), Column("id", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    with pytest.raises(MissingColumnError):
        sqlrules.compile(Filter, table, column_map={"age": "not-a-column"})  # type: ignore[dict-item]


def test_column_map_invalid_value_does_not_fall_through() -> None:
    """A present but invalid column_map entry must not bind the table column."""
    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    with pytest.raises(MissingColumnError):
        sqlrules.compile(Filter, table, column_map={"age": "not-a-column"})  # type: ignore[dict-item]


def test_resolve_column_alias_kwarg_without_aliases_list() -> None:
    from sqlrules.columns import resolve_column

    table = Table("users", MetaData(), Column("user_age", Integer))
    column = resolve_column("years", table, alias="user_age")
    assert column is table.c.user_age


def test_resolve_column_duplicate_alias_and_field_name() -> None:
    from sqlrules.columns import resolve_column

    table = Table("users", MetaData(), Column("age", Integer))
    column = resolve_column("age", table, aliases=("age", "age"))
    assert column is table.c.age


def test_multiple_of_non_comparable_value() -> None:
    from sqlrules.ir import CompilationContext, Constraint
    from sqlrules.translators import default_registry

    registry = default_registry()
    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        registry.translate(
            Constraint("age", "multiple_of", object()),
            Column("age", Integer),
            CompilationContext(),
        )


def test_predicate_unsupported() -> None:
    from annotated_types import Predicate

    table = Table("users", MetaData(), Column("age", Integer))

    class Filter(BaseModel):
        age: Annotated[int, Predicate(lambda value: value > 0)]

    with pytest.raises(UnsupportedConstraintError, match="predicate"):
        sqlrules.compile(Filter, table)

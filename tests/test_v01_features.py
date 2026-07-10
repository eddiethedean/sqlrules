from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

import pytest
from annotated_types import Interval
from pydantic import AfterValidator, BaseModel, Field, StringConstraints, conint, constr
from sqlalchemy import Column, Date, DateTime, Integer, MetaData, Numeric, String, Table
from sqlalchemy.dialects import sqlite

import sqlrules
from sqlrules import MissingColumnError, SQLRulesWarning, UnsupportedConstraintError


@pytest.fixture
def people() -> Table:
    return Table(
        "people",
        MetaData(),
        Column("age", Integer),
        Column("score", Numeric),
        Column("name", String),
        Column("active", Integer),
        Column("born", Date),
        Column("created", DateTime),
        Column("status", String),
        Column("qty", Integer),
        Column("user_age", Integer),
    )


def test_pattern_raises_by_default(people: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        sqlrules.compile(Filter, people)


def test_pattern_warn_keeps_supported_constraints(people: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(min_length=2, pattern=r"^A")]

    with pytest.warns(SQLRulesWarning, match="pattern"):
        rules = sqlrules.compile(Filter, people, on_unsupported="warn")

    assert list(rules) == ["name"]
    assert len(rules["name"]) == 1


def test_pattern_ignore(people: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    assert sqlrules.compile(Filter, people, on_unsupported="ignore") == {}


def test_decimal_precision_unsupported(people: Table) -> None:
    class Filter(BaseModel):
        score: Annotated[Decimal, Field(max_digits=5, decimal_places=2, ge=0)]

    with pytest.raises(UnsupportedConstraintError, match="max_digits|decimal_places"):
        sqlrules.compile(Filter, people)


def test_after_validator_unsupported(people: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, AfterValidator(lambda value: value)]

    with pytest.raises(UnsupportedConstraintError, match="AfterValidator"):
        sqlrules.compile(Filter, people)


def test_interval_and_conint(people: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Interval(gt=0, le=100)]
        qty: conint(ge=18, le=65)

    rules = sqlrules.compile(Filter, people)
    assert list(rules) == ["age", "qty"]
    assert len(rules["age"]) == 2
    assert len(rules["qty"]) == 2


def test_constr_and_string_constraints(people: Table) -> None:
    class Filter(BaseModel):
        name: constr(min_length=2, max_length=10)
        status: Annotated[str, StringConstraints(min_length=1)]

    rules = sqlrules.compile(Filter, people)
    assert len(rules["name"]) == 2
    assert len(rules["status"]) == 1


def test_string_constraints_with_pattern_raises(people: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, StringConstraints(min_length=1, pattern=r"x")]

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        sqlrules.compile(Filter, people)


def test_float_decimal_date_datetime_bool_literal(people: Table) -> None:
    class Filter(BaseModel):
        score: Annotated[float, Field(gt=0.0, lt=100.0)]
        qty: Annotated[Decimal, Field(ge=Decimal("1"), le=Decimal("10"))]
        born: Annotated[date, Field(ge=date(2000, 1, 1))]
        created: Annotated[datetime, Field(le=datetime(2030, 1, 1))]
        active: Literal[True]

    rules = sqlrules.compile(Filter, people)
    assert list(rules) == ["score", "qty", "born", "created", "active"]
    assert len(rules["score"]) == 2
    compiled = str(rules["born"][0].compile(dialect=sqlite.dialect()))
    assert "born" in compiled


def test_lt_constraint(people: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(lt=65)]

    rules = sqlrules.compile(Filter, people)
    assert len(rules["age"]) == 1


def test_deterministic_field_order(people: Table) -> None:
    class Filter(BaseModel):
        qty: Annotated[int, Field(gt=0)]
        age: Annotated[int, Field(ge=18)]
        name: Annotated[str, Field(min_length=1)]

    rules = sqlrules.compile(Filter, people)
    assert list(rules) == ["qty", "age", "name"]


def test_field_alias_resolves_column(people: Table) -> None:
    class Filter(BaseModel):
        years: Annotated[int, Field(ge=18, alias="user_age")]

    rules = sqlrules.compile(Filter, people)
    assert "years" in rules


def test_unsupported_container_type(people: Table) -> None:
    class Filter(BaseModel):
        age: list[int]

    with pytest.raises(UnsupportedConstraintError, match="list"):
        sqlrules.compile(Filter, people)


def test_unsupported_uuid_type(people: Table) -> None:
    class Filter(BaseModel):
        age: UUID  # reuse people.age column name to isolate type failure

    with pytest.raises(UnsupportedConstraintError, match="UUID"):
        sqlrules.compile(Filter, people)


def test_enum_and_literal(people: Table) -> None:
    class Status(Enum):
        ACTIVE = "ACTIVE"
        DISABLED = "DISABLED"

    class Filter(BaseModel):
        status: Status

    rules = sqlrules.compile(Filter, people)
    assert len(rules["status"]) == 1


def test_missing_column_still_raises() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    table = Table("users", MetaData(), Column("id", Integer))
    with pytest.raises(MissingColumnError):
        sqlrules.compile(Filter, table)

from enum import Enum
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Table
from sqlalchemy.dialects import sqlite

import sqlrules


class Status(Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class LiteralFilter(BaseModel):
    status: Literal["ACTIVE", "DISABLED"]


class EnumFilter(BaseModel):
    status: Status


def _sql(expr: object) -> str:
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_literal_compile(users: Table) -> None:
    rules = sqlrules.compile(LiteralFilter, users)
    assert "status" in rules
    assert len(rules["status"]) == 1
    compiled = _sql(rules["status"][0]).upper()
    assert "IN" in compiled
    assert "ACTIVE" in compiled
    assert "DISABLED" in compiled


def test_enum_compile(users: Table) -> None:
    rules = sqlrules.compile(EnumFilter, users)
    assert "status" in rules
    assert len(rules["status"]) == 1
    compiled = _sql(rules["status"][0]).upper()
    assert "IN" in compiled
    assert "ACTIVE" in compiled
    assert "DISABLED" in compiled

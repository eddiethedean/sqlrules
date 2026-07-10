from enum import Enum
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Table

import sqlrules


class Status(Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class LiteralFilter(BaseModel):
    status: Literal["ACTIVE", "DISABLED"]


class EnumFilter(BaseModel):
    status: Status


def test_literal_compile(users: Table) -> None:
    rules = sqlrules.compile(LiteralFilter, users)
    assert "status" in rules
    assert len(rules["status"]) == 1


def test_enum_compile(users: Table) -> None:
    rules = sqlrules.compile(EnumFilter, users)
    assert "status" in rules
    assert len(rules["status"]) == 1

from enum import Enum
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Table

import sqlrules
from assert_sql import assert_expr_equals, assert_rules_sql


class Status(Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class LiteralFilter(BaseModel):
    status: Literal["ACTIVE", "DISABLED"]


class EnumFilter(BaseModel):
    status: Status


def test_literal_compile(users: Table) -> None:
    rules = sqlrules.compile(LiteralFilter, users)
    assert_rules_sql(
        rules,
        {"status": ["users.status IN ('ACTIVE', 'DISABLED')"]},
    )
    assert_expr_equals(rules["status"][0], users.c.status.in_(("ACTIVE", "DISABLED")))


def test_enum_compile(users: Table) -> None:
    rules = sqlrules.compile(EnumFilter, users)
    assert_rules_sql(
        rules,
        {"status": ["users.status IN ('ACTIVE', 'DISABLED')"]},
    )
    assert_expr_equals(rules["status"][0], users.c.status.in_(("ACTIVE", "DISABLED")))

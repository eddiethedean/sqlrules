from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table
from sqlalchemy.dialects import sqlite

import sqlrules


class UserFilter(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=50)]


def _sql(expr: object) -> str:
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_string_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert "name" in rules
    assert len(rules["name"]) == 2

    name_sql = [_sql(expr) for expr in rules["name"]]
    assert any("length" in s.lower() and ">=" in s and "2" in s for s in name_sql)
    assert any("length" in s.lower() and "<=" in s and "50" in s for s in name_sql)

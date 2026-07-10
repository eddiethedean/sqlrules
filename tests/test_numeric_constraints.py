from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table
from sqlalchemy.dialects import sqlite

import sqlrules


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]
    id: Annotated[int, Field(gt=0, multiple_of=2)]


def _sql(expr: object) -> str:
    return str(
        expr.compile(  # type: ignore[union-attr]
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_numeric_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert set(rules) == {"age", "id"}
    assert len(rules["age"]) == 2
    assert len(rules["id"]) == 2

    age_sql = [_sql(expr) for expr in rules["age"]]
    assert any(">=" in s and "18" in s for s in age_sql)
    assert any("<=" in s and "65" in s for s in age_sql)

    id_sql = [_sql(expr) for expr in rules["id"]]
    assert any(">" in s and "0" in s for s in id_sql)
    assert any("% 2 = 0" in s or "% 2=0" in s.replace(" ", "") for s in id_sql)

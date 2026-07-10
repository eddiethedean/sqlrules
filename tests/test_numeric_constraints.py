from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table
from sqlalchemy.dialects import sqlite

import sqlrules


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]
    id: Annotated[int, Field(gt=0, multiple_of=2)]


def test_numeric_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert set(rules) == {"age", "id"}
    assert len(rules["age"]) == 2
    assert len(rules["id"]) == 2

    compiled = str(rules["age"][0].compile(dialect=sqlite.dialect()))
    assert "age" in compiled

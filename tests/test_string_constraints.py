from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table

import sqlrules


class UserFilter(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=50)]


def test_string_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert "name" in rules
    assert len(rules["name"]) == 2

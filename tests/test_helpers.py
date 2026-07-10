from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table

import sqlrules


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]


def test_where_flattens_rules(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert sqlrules.where(rules) == sqlrules.flatten(rules)
    assert len(sqlrules.where(rules)) == 2

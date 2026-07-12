from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table, func

import sqlrules
from assert_sql import assert_expr_equals, assert_rules_sql


class UserFilter(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=50)]


def test_string_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert_rules_sql(
        rules,
        {
            "name": ["length(users.name) >= 2", "length(users.name) <= 50"],
        },
    )
    assert_expr_equals(rules["name"][0], func.length(users.c.name) >= 2)
    assert_expr_equals(rules["name"][1], func.length(users.c.name) <= 50)

from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table

import sqlrules
from assert_sql import assert_expr_equals, assert_rules_sql


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]
    id: Annotated[int, Field(gt=0, multiple_of=2)]


def test_numeric_constraints_compile(users: Table) -> None:
    rules = sqlrules.compile(UserFilter, users)

    assert_rules_sql(
        rules,
        {
            "age": ["users.age >= 18", "users.age <= 65"],
            "id": ["users.id > 0", "users.id % 2 = 0"],
        },
    )
    assert_expr_equals(rules["age"][0], users.c.age >= 18)
    assert_expr_equals(rules["age"][1], users.c.age <= 65)
    assert_expr_equals(rules["id"][0], users.c.id > 0)
    assert_expr_equals(rules["id"][1], users.c.id % 2 == 0)

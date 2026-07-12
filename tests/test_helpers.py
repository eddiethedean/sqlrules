from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Table

import sqlrules
from assert_sql import assert_expr_equals, assert_rules_sql, sql_literal


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]


def test_where_flattens_rules(users: Table) -> None:
    """where()/flatten() concatenate field expressions in declaration order."""
    rules = sqlrules.compile(UserFilter, users)

    assert sqlrules.where is sqlrules.flatten or sqlrules.where(rules) == sqlrules.flatten(rules)
    flat = sqlrules.where(rules)
    assert [sql_literal(e) for e in flat] == ["users.age >= 18", "users.age <= 65"]
    assert_expr_equals(flat[0], users.c.age >= 18)
    assert_expr_equals(flat[1], users.c.age <= 65)
    assert_rules_sql(rules, {"age": ["users.age >= 18", "users.age <= 65"]})

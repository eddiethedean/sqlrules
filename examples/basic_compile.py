"""Minimal compile → select() example (core only).

Run from the repo root after ``pip install sqlrules`` (or ``make install``):

    python examples/basic_compile.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules

users = Table(
    "users",
    MetaData(),
    Column("age", Integer),
    Column("name", String),
)


class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]
    name: Annotated[str, Field(min_length=2)]


def main() -> None:
    rules = sqlrules.compile(UserFilter, users)
    stmt = users.select().where(*sqlrules.where(rules))
    print("fields:", sorted(rules))
    print(stmt)


if __name__ == "__main__":
    main()

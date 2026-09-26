"""Minimal compile → select() example (core only).

Run from the repo root after ``pip install sqlrules`` (or ``make install``):

    python examples/basic_compile.py
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlrules_sqlite import SQLitePlugin

import sqlrules
from sqlrules import Compiler, RuleSchema

users = Table(
    "users",
    MetaData(),
    Column("age", Integer),
    Column("name", String),
)


class UserFilter(RuleSchema):
    age: Annotated[int, Field(ge=18, le=65)]
    name: Annotated[str, Field(min_length=2)]


def main() -> None:
    compiler = Compiler(plugins=[SQLitePlugin()])
    compiled = compiler.compile(UserFilter, users)
    stmt = users.select().where(*sqlrules.where(compiled))
    print("fields:", [field.name for field in compiled.fields])
    print(stmt)


if __name__ == "__main__":
    main()

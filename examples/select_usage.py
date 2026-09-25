"""Compile rules and show a SQLAlchemy select() string.

Run from the repo root after installing SQLRules and its SQLite provider.

    python examples/select_usage.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlrules_sqlite import SQLitePlugin

import sqlrules
from sqlrules import Compiler, RuleSchema

items = Table(
    "items",
    MetaData(),
    Column("qty", Integer),
    Column("status", String),
)


class ItemFilter(RuleSchema):
    qty: Annotated[int, Field(ge=1, le=100)]
    status: Literal["active", "pending"]


def main() -> None:
    compiler = Compiler(plugins=[SQLitePlugin()])
    compiled = compiler.compile(ItemFilter, items)
    stmt = items.select().where(*sqlrules.where(compiled))
    # Compile without a live DB — expressions use bound parameters.
    print(stmt.compile(compile_kwargs={"literal_binds": False}))


if __name__ == "__main__":
    main()

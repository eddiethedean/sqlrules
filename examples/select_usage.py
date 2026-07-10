"""Compile rules and show a SQLAlchemy select() string.

Run:

    python examples/select_usage.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules

items = Table(
    "items",
    MetaData(),
    Column("qty", Integer),
    Column("status", String),
)


class ItemFilter(BaseModel):
    qty: Annotated[int, Field(ge=1, le=100)]
    status: Literal["active", "pending"]


def main() -> None:
    rules = sqlrules.compile(ItemFilter, items)
    stmt = items.select().where(*sqlrules.where(rules))
    # Compile without a live DB — expressions use bound parameters.
    print(stmt.compile(compile_kwargs={"literal_binds": False}))


if __name__ == "__main__":
    main()

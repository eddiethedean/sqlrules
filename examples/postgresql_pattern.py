"""PostgreSQL plugin: pattern + JSON marker.

Requires::

    pip install "sqlrules[postgresql]"

Run:

    python examples/postgresql_pattern.py
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlrules_postgresql import PostgresPlugin

import sqlrules
from sqlrules import Compiler, JsonContains, UnsupportedConstraintError

table = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", JSONB),
)


class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]


def main() -> None:
    # Without a plugin, pattern raises (core has no portable regex).
    try:
        sqlrules.compile(RowFilter, table)
    except UnsupportedConstraintError as exc:
        print("core alone:", exc)

    # dialect= is a hint only — plugins must be passed explicitly.
    compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
    rules = compiler.compile(RowFilter, table)
    stmt = table.select().where(*sqlrules.where(rules))
    print("with plugin fields:", sorted(rules))
    print(stmt)


if __name__ == "__main__":
    main()

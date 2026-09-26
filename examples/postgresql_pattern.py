"""PostgreSQL plugin: pattern + JSON marker.

Requires::

    pip install "sqlrules[postgresql]"

Run:

    python examples/postgresql_pattern.py
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlrules_postgresql import PostgresPlugin

import sqlrules
from sqlrules import Compiler, JsonContains, RuleSchema

table = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", JSONB),
)


class RowFilter(RuleSchema):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]


def main() -> None:
    compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
    compiled = compiler.compile(RowFilter, table)
    stmt = table.select().where(*sqlrules.where(compiled))
    print("with plugin fields:", [field.name for field in compiled.fields])
    print("\n".join(line.rstrip() for line in str(stmt).splitlines()))


if __name__ == "__main__":
    main()

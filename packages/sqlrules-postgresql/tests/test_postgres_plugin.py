from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlrules_postgresql import PostgresPlugin, __version__

from sqlrules import Compiler
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "0.3.0"


def test_conformance() -> None:
    run_basic_conformance(PostgresPlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[PostgresPlugin()],
        dialect="postgresql",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(dialect=postgresql.dialect()))
    assert "~" in compiled

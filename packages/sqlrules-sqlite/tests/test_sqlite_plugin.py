from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects import sqlite
from sqlrules_sqlite import SQLitePlugin, __version__

from sqlrules import Compiler
from sqlrules.conformance import run_basic_conformance


def test_version() -> None:
    assert __version__ == "0.3.0"


def test_conformance() -> None:
    run_basic_conformance(SQLitePlugin(), operator="pattern")


def test_pattern_compiles() -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    table = Table("items", MetaData(), Column("name", String))
    rules = Compiler(
        plugins=[SQLitePlugin()],
        dialect="sqlite",
        cache=False,
    ).compile(Filter, table)
    compiled = str(rules["name"][0].compile(dialect=sqlite.dialect()))
    assert "REGEXP" in compiled

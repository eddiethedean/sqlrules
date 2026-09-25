"""Compile benchmarks for small, medium, and large RuleSchema classes.

Run::

    python -m benchmarks.bench_compile
"""

from __future__ import annotations

import timeit
from typing import Annotated, Any

from pydantic import Field, create_model
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlrules_sqlite import SQLitePlugin

import sqlrules
from sqlrules.models import RuleSchema


def _build_model(n_fields: int) -> type[RuleSchema]:
    fields: dict[str, Any] = {}
    for i in range(n_fields):
        if i % 2 == 0:
            fields[f"n{i}"] = (Annotated[int, Field(ge=0, le=100)], ...)
        else:
            fields[f"s{i}"] = (Annotated[str, Field(min_length=1, max_length=50)], ...)
    return create_model(f"Filter{n_fields}", __base__=RuleSchema, **fields)


def _build_table(n_fields: int) -> Table:
    metadata = MetaData()
    columns: list[Column[Any]] = []
    for i in range(n_fields):
        if i % 2 == 0:
            columns.append(Column(f"n{i}", Integer))
        else:
            columns.append(Column(f"s{i}", String))
    return Table(f"t{n_fields}", metadata, *columns)


def _bench(label: str, model: type[RuleSchema], table: Table, *, repeats: int = 50) -> None:
    compiler = sqlrules.Compiler(plugins=[SQLitePlugin()])
    normalized = compiler.compile_model(model)
    normalization = min(
        timeit.repeat(lambda: compiler.compile_model(model), number=1, repeat=repeats)
    )
    binding = min(timeit.repeat(lambda: compiler.bind(normalized, table), number=1, repeat=repeats))
    full = min(timeit.repeat(lambda: compiler.compile(model, table), number=1, repeat=repeats))
    print(
        f"{label:12} normalize={normalization * 1000:8.3f} ms  "
        f"bind={binding * 1000:8.3f} ms  full={full * 1000:8.3f} ms"
    )


def main() -> None:
    print("SQLRules compile benchmarks (best of repeated local runs)")
    print("-" * 56)
    for size, n in (("small", 5), ("medium", 25), ("large", 100)):
        model = _build_model(n)
        table = _build_table(n)
        _bench(f"{size} ({n})", model, table)


if __name__ == "__main__":
    main()

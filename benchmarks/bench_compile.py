"""Compile benchmarks for small / medium / large models (cold vs warm cache).

Illustrative targets from docs/PERFORMANCE.md (not enforced):
  Small  (< 5 fields)   < 0.5 ms
  Medium (~25 fields)   < 2 ms
  Large  (100+ fields)  < 10 ms

Run::

    python -m benchmarks.bench_compile
"""

from __future__ import annotations

import timeit
from typing import Annotated, Any

from pydantic import BaseModel, Field, create_model
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules
from sqlrules.cache import ModelIRCache


def _build_model(n_fields: int) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for i in range(n_fields):
        if i % 2 == 0:
            fields[f"n{i}"] = (Annotated[int, Field(ge=0, le=100)], ...)
        else:
            fields[f"s{i}"] = (Annotated[str, Field(min_length=1, max_length=50)], ...)
    return create_model(f"Filter{n_fields}", **fields)  # type: ignore[call-overload]


def _build_table(n_fields: int) -> Table:
    metadata = MetaData()
    columns: list[Column[Any]] = []
    for i in range(n_fields):
        if i % 2 == 0:
            columns.append(Column(f"n{i}", Integer))
        else:
            columns.append(Column(f"s{i}", String))
    return Table(f"t{n_fields}", metadata, *columns)


def _bench(label: str, model: type[BaseModel], table: Table, *, repeats: int = 50) -> None:
    cache = ModelIRCache()
    compiler = sqlrules.Compiler(cache=True, model_cache=cache)

    # Cold: empty cache
    cache.clear()
    cold = timeit.timeit(lambda: compiler.compile(model, table), number=1)

    # Warm: IR already cached
    warm = min(timeit.repeat(lambda: compiler.compile(model, table), number=1, repeat=repeats))

    print(f"{label:12} cold={cold * 1000:8.3f} ms  warm={warm * 1000:8.3f} ms")


def main() -> None:
    print("SQLRules compile benchmarks (cache cold vs warm)")
    print("-" * 56)
    for size, n in (("small", 5), ("medium", 25), ("large", 100)):
        model = _build_model(n)
        table = _build_table(n)
        _bench(f"{size} ({n})", model, table)


if __name__ == "__main__":
    main()

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StrictInt
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select
from sqlrules_sqlite import SQLitePlugin, register_regexp

from sqlrules import Compiler, RuleConfig, RuleSchema, notwhere, where


def test_where_and_notwhere_partition_rows_with_nulls_and_bad_values() -> None:
    class Rules(RuleSchema):
        id: int
        payload: int | None = Field(ge=0, multiple_of=2)
        name: Annotated[str, Field(min_length=2, pattern=r"^[A-Z][a-z]+$")]
        status: Literal["ready", "pending"]

    table = Table(
        "records",
        MetaData(),
        Column("id", Integer, primary_key=True),
        # TEXT storage exercises guarded text-to-integer conversion.
        Column("payload", String),
        Column("name", String),
        Column("status", String),
    )
    engine = create_engine("sqlite://")
    table.create(engine)
    rows = [
        {"id": 1, "payload": "12", "name": "Ada", "status": "ready"},
        {"id": 2, "payload": None, "name": "Bo", "status": "pending"},
        {"id": 3, "payload": "broken", "name": "Cy", "status": "ready"},
        {"id": 4, "payload": -1, "name": "Dee", "status": "ready"},
        {"id": 5, "payload": 12, "name": "E", "status": "ready"},
        {"id": 6, "payload": 12, "name": "Fox", "status": "unknown"},
        {"id": 7, "payload": 3, "name": "Gus", "status": "ready"},
    ]
    with engine.begin() as connection:
        register_regexp(connection.connection.driver_connection)
        connection.execute(insert(table), rows)
        compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
        matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
        failed = set(connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars())

    assert matched == {1, 2}
    assert failed == {3, 4, 5, 6, 7}
    assert matched.isdisjoint(failed)
    assert matched | failed == {1, 2, 3, 4, 5, 6, 7}
    engine.dispose()


def test_strict_scalar_requires_runtime_sqlite_storage_class() -> None:
    class Rules(RuleSchema):
        payload: StrictInt

    table = Table(
        "records",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", String),
    )
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(table),
            [
                {"id": 1, "payload": 5},
                {"id": 2, "payload": "5"},
                {"id": 3, "payload": "invalid"},
                {"id": 4, "payload": None},
            ],
        )
        compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
        matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
        failed = set(connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars())
    # TEXT affinity stores both Python integers and numeric strings as text,
    # so SQLite cannot prove that any row has an integer storage class.
    assert matched == set()
    assert failed == {1, 2, 3, 4}
    engine.dispose()


def test_sqlite_mixed_integer_affinity_rejects_non_integer_storage() -> None:
    class Rules(RuleSchema):
        payload: StrictInt

    table = Table(
        "records",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", Integer),
    )
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(table),
            [
                {"id": 1, "payload": 5},
                {"id": 2, "payload": "not-an-integer"},
                {"id": 3, "payload": None},
            ],
        )
        compiled = Compiler(plugins=[SQLitePlugin()]).compile(Rules, table)
        matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
        failed = set(connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars())
    assert matched == {1}
    assert failed == {2, 3}
    engine.dispose()


def test_empty_rules_select_nothing_with_notwhere() -> None:
    class EmptyRules(RuleSchema):
        __rule_config__ = RuleConfig(allow_empty=True)

    table = Table(
        "records",
        MetaData(),
        Column("id", Integer, primary_key=True),
    )
    engine = create_engine("sqlite://")
    table.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(table), [{"id": 1}, {"id": 2}])
        compiled = Compiler(plugins=[SQLitePlugin()]).compile(EmptyRules, table)
        matched = connection.execute(select(table.c.id).where(*where(compiled))).all()
        failed = connection.execute(select(table.c.id).where(*notwhere(compiled))).all()
    assert matched == [(1,), (2,)]
    assert failed == []
    engine.dispose()


def test_regexp_udf_treats_mixed_storage_values_as_non_matches() -> None:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        register_regexp(connection.connection.driver_connection)
        assert connection.exec_driver_sql("SELECT 5 REGEXP '^5$'").scalar() == 0
        assert connection.exec_driver_sql("SELECT '5' REGEXP '^5$'").scalar() == 1
    engine.dispose()

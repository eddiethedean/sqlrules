from __future__ import annotations

import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import pytest
from pydantic import Field
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Time,
    create_engine,
    insert,
    select,
)
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlrules_mssql import MssqlPlugin
from sqlrules_mysql import MysqlPlugin
from sqlrules_postgresql import PostgresPlugin

from sqlrules import (
    ArrayContains,
    Compiler,
    FullTextMatch,
    JsonContains,
    JsonHasKey,
    RangeContains,
    RuleSchema,
    notwhere,
    where,
)


class IntegerPayloadRules(RuleSchema):
    payload: int | None = Field(ge=0)


class StrictIntegerPayloadRules(RuleSchema):
    payload: int | None = Field(strict=True)


class PositiveFloatPayloadRules(RuleSchema):
    payload: float = Field(gt=0)


class NativeScalarRules(RuleSchema):
    flag: bool
    count: Annotated[int, Field(ge=0, multiple_of=2)]
    ratio: Annotated[float, Field(gt=0)]
    amount: Decimal
    label: Annotated[str, Field(min_length=2, max_length=12)]
    state: Literal["ready", "pending"]
    day: date
    created: datetime
    clock: time
    optional_count: int | None
    required_note: str


class UUIDRules(RuleSchema):
    token: UUID


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version"),
    [
        ("postgresql", PostgresPlugin, (16, 0)),
        ("mysql", MysqlPlugin, (8, 0, 36)),
        ("mssql", MssqlPlugin, (16, 0)),
    ],
)
def test_live_backend_match_and_fail_sets_partition(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
) -> None:
    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_rules_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", String(128)),
    )
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [
                    {"id": 1, "payload": "12"},
                    {"id": 2, "payload": "malformed"},
                    {"id": 3, "payload": None},
                    {"id": 4, "payload": "-1"},
                    {"id": 5, "payload": "9223372036854775808"},
                ],
            )
            provider = provider_type(server_version=server_version)
            compiled = Compiler(plugins=[provider]).compile(IntegerPayloadRules, table)
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1, 3}
        assert failed == {2, 4, 5}
        assert matched.isdisjoint(failed)
        assert matched | failed == {1, 2, 3, 4, 5}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version"),
    [
        ("postgresql", PostgresPlugin, (16, 0)),
        ("mysql", MysqlPlugin, (8, 0, 36)),
        ("mssql", MssqlPlugin, (16, 0)),
    ],
)
def test_live_strict_text_mismatch_is_complemented_by_notwhere(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
) -> None:
    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_strict_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", String(128)),
    )
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [{"id": 1, "payload": "12"}, {"id": 2, "payload": None}],
            )
            compiled = Compiler(plugins=[provider_type(server_version=server_version)]).compile(
                StrictIntegerPayloadRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {2}
        assert failed == {1}
        assert matched | failed == {1, 2}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version"),
    [
        ("postgresql", PostgresPlugin, (16, 0)),
        ("mssql", MssqlPlugin, (16, 0)),
    ],
)
def test_live_float_text_conversion_rejects_malformed_and_nonfinite_text(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
) -> None:
    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_float_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", String(128)),
    )
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [
                    {"id": 1, "payload": "2.5"},
                    {"id": 2, "payload": "malformed"},
                    {"id": 3, "payload": "Infinity"},
                    {"id": 4, "payload": "-1"},
                    {"id": 5, "payload": "1e2"},
                ],
            )
            compiled = Compiler(plugins=[provider_type(server_version=server_version)]).compile(
                PositiveFloatPayloadRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1, 5}
        assert failed == {2, 3, 4}
        assert matched.isdisjoint(failed)
        assert matched | failed == {1, 2, 3, 4, 5}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version", "collation"),
    [
        ("postgresql", PostgresPlugin, (16, 0), "C"),
        ("mysql", MysqlPlugin, (8, 0, 36), "utf8mb4_bin"),
        ("mssql", MssqlPlugin, (16, 0), "Latin1_General_100_BIN2"),
    ],
)
def test_live_native_scalar_constraints_and_null_partition(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
    collation: str,
) -> None:
    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_native_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("flag", Boolean),
        Column("count", BigInteger),
        Column("ratio", Float),
        Column("amount", Numeric(12, 2)),
        Column("label", String(32, collation=collation)),
        Column("state", String(16, collation=collation)),
        Column("day", Date),
        Column("created", DateTime),
        Column("clock", Time),
        Column("optional_count", Integer, nullable=True),
        Column("required_note", String(32), nullable=True),
    )
    valid = {
        "flag": True,
        "count": 2,
        "ratio": 2.5,
        "amount": Decimal("10.25"),
        "label": "Ada",
        "state": "ready",
        "day": date(2020, 1, 2),
        "created": datetime(2020, 1, 2, 12, 30),
        "clock": time(12, 30),
        "optional_count": 4,
        "required_note": "present",
    }
    rows = [
        {"id": 1, **valid},
        {"id": 2, **(valid | {"count": 3})},
        {"id": 3, **(valid | {"label": "A"})},
        {"id": 4, **(valid | {"state": "unknown"})},
        {"id": 5, **(valid | {"optional_count": None, "required_note": None})},
    ]
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), rows)
            compiled = Compiler(plugins=[provider_type(server_version=server_version)]).compile(
                NativeScalarRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == {2, 3, 4, 5}
        assert matched.isdisjoint(failed)
        assert matched | failed == {1, 2, 3, 4, 5}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version", "source_type"),
    [
        ("postgresql", PostgresPlugin, (16, 0), PostgreSQLUUID(as_uuid=True)),
        ("mssql", MssqlPlugin, (16, 0), UNIQUEIDENTIFIER(as_uuid=True)),
    ],
)
def test_live_uuid_type_only_rule(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
    source_type: Any,
) -> None:
    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_uuid_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("token", source_type, nullable=True),
    )
    token = uuid4()
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), [{"id": 1, "token": token}, {"id": 2, "token": None}])
            compiled = Compiler(plugins=[provider_type(server_version=server_version)]).compile(
                UUIDRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == {2}
        assert matched | failed == {1, 2}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version", "json_type"),
    [
        ("postgresql", PostgresPlugin, (16, 0), JSONB),
        ("mysql", MysqlPlugin, (8, 0, 36), None),
        ("mssql", MssqlPlugin, (16, 0, 160), String(1024)),
    ],
)
def test_live_json_markers_handle_values_null_and_malformed_documents(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
    json_type: Any,
) -> None:
    from sqlalchemy import JSON

    class JsonRules(RuleSchema):
        meta: Annotated[
            dict[str, Any],
            JsonContains({"active": True}),
            JsonHasKey("active"),
        ]

    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    selected_json_type = json_type or JSON()
    table = Table(
        f"sr_json_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("meta", selected_json_type, nullable=True),
    )
    if backend == "mssql":
        rows = [
            {"id": 1, "meta": '{"active":true}'},
            {"id": 2, "meta": '{"active":false}'},
            {"id": 3, "meta": "{}"},
            {"id": 4, "meta": None},
            {"id": 5, "meta": "malformed"},
        ]
        expected = {1, 2, 3, 4, 5}
    else:
        rows = [
            {"id": 1, "meta": {"active": True}},
            {"id": 2, "meta": {"active": False}},
            {"id": 3, "meta": {}},
            {"id": 4, "meta": None},
        ]
        expected = {1, 2, 3, 4}
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), rows)
            if backend == "mssql":
                provider = provider_type(
                    server_version=server_version[:2], compatibility_level=server_version[2]
                )
            else:
                provider = provider_type(server_version=server_version)
            compiled = Compiler(plugins=[provider]).compile(JsonRules, table)
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == expected - {1}
        assert matched.isdisjoint(failed)
        assert matched | failed == expected
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_live_postgresql_array_and_range_markers() -> None:
    url = os.getenv("SQLRULES_TEST_POSTGRESQL_URL")
    if not url:
        pytest.skip("SQLRULES_TEST_POSTGRESQL_URL is not configured")

    from psycopg.types.range import Range

    class StructuredRules(RuleSchema):
        tags: Annotated[list[str], ArrayContains(["admin"])]
        span: Annotated[int, RangeContains(5)]

    engine = create_engine(url)
    table = Table(
        f"sr_structured_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("tags", ARRAY(String), nullable=True),
        Column("span", INT4RANGE, nullable=True),
    )
    rows = [
        {"id": 1, "tags": ["admin", "staff"], "span": Range(1, 10)},
        {"id": 2, "tags": ["admin"], "span": Range(10, 20)},
        {"id": 3, "tags": ["viewer"], "span": Range(1, 10)},
        {"id": 4, "tags": None, "span": None},
    ]
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), rows)
            compiled = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))]).compile(
                StructuredRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == {2, 3, 4}
        assert matched | failed == {1, 2, 3, 4}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


def test_live_mysql_fulltext_marker_uses_an_indexed_source() -> None:
    url = os.getenv("SQLRULES_TEST_MYSQL_URL")
    if not url:
        pytest.skip("SQLRULES_TEST_MYSQL_URL is not configured")

    class FullTextRules(RuleSchema):
        body: Annotated[str, FullTextMatch("database")]

    engine = create_engine(url)
    table = Table(
        f"sr_fulltext_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("body", String(255)),
    )
    index = Index(f"ix_fulltext_{uuid4().hex[:8]}", table.c.body, mysql_prefix="FULLTEXT")
    try:
        table.create(engine)
        index.create(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [
                    {"id": 1, "body": "sqlrules database predicates"},
                    {"id": 2, "body": "apples and oranges"},
                ],
            )
            compiled = Compiler(plugins=[MysqlPlugin(server_version=(8, 0, 36))]).compile(
                FullTextRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == {2}
        assert matched | failed == {1, 2}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()


@pytest.mark.parametrize(
    ("backend", "provider_type", "server_version", "collation"),
    [
        ("postgresql", PostgresPlugin, (16, 0), "C"),
        ("mysql", MysqlPlugin, (8, 0, 36), "utf8mb4_bin"),
    ],
)
def test_live_pattern_marker_matches_supported_text(
    backend: str,
    provider_type: Any,
    server_version: tuple[int, ...],
    collation: str,
) -> None:
    class PatternRules(RuleSchema):
        label: Annotated[str, Field(pattern=r"^[A-Z][a-z]+$")]

    url = os.getenv(f"SQLRULES_TEST_{backend.upper()}_URL")
    if not url:
        pytest.skip(f"SQLRULES_TEST_{backend.upper()}_URL is not configured")

    engine = create_engine(url)
    table = Table(
        f"sr_pattern_{backend}_{uuid4().hex[:10]}",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("label", String(32, collation=collation)),
    )
    try:
        table.create(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [{"id": 1, "label": "Ada"}, {"id": 2, "label": "lower"}],
            )
            compiled = Compiler(plugins=[provider_type(server_version=server_version)]).compile(
                PatternRules, table
            )
            matched = set(connection.execute(select(table.c.id).where(*where(compiled))).scalars())
            failed = set(
                connection.execute(select(table.c.id).where(*notwhere(compiled))).scalars()
            )
        assert matched == {1}
        assert failed == {2}
        assert matched | failed == {1, 2}
    finally:
        table.drop(engine, checkfirst=True)
        engine.dispose()

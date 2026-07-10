"""SQLRules 0.2 feature tests: two-phase compile, cache, diagnostics, types, pattern IR."""

from __future__ import annotations

import warnings
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, Time
from sqlalchemy.dialects import sqlite

import sqlrules
from sqlrules import SQLRulesWarning, UnsupportedConstraintError
from sqlrules.cache import ModelIRCache
from sqlrules.constraints import pattern_text
from sqlrules.ir import Constraint, PatternSpec
from sqlrules.translators import default_registry


@pytest.fixture
def items() -> Table:
    return Table(
        "items",
        MetaData(),
        Column("id", String),
        Column("name", String),
        Column("score", Numeric),
        Column("starts", Time),
        Column("created", DateTime),
        Column("age", Integer),
    )


def test_two_phase_equals_oneshot(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18, le=65)]
        name: Annotated[str, Field(min_length=2)]

    compiler = sqlrules.Compiler(cache=False)
    oneshot = compiler.compile(Filter, items)
    model_ir = compiler.compile_model(Filter)
    bound = compiler.bind(model_ir, items)

    assert list(oneshot) == list(bound) == ["age", "name"]
    assert len(oneshot["age"]) == len(bound["age"]) == 2
    assert len(oneshot["name"]) == len(bound["name"]) == 1


def test_metadata_cache_reuses_model_ir(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    cache = ModelIRCache()
    compiler = sqlrules.Compiler(cache=True, model_cache=cache)

    first = compiler.compile_model(Filter)
    second = compiler.compile_model(Filter)
    assert first is second
    assert first.fields[0].constraints == second.fields[0].constraints

    other = Table("other", MetaData(), Column("age", Integer))
    rules_a = compiler.bind(first, items)
    rules_b = compiler.bind(second, other)
    assert "age" in rules_a and "age" in rules_b


def test_cache_disabled_builds_fresh_ir(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    cache = ModelIRCache()
    compiler = sqlrules.Compiler(cache=False, model_cache=cache)
    first = compiler.compile_model(Filter)
    second = compiler.compile_model(Filter)
    assert first is not second
    assert cache.get(Filter) is None


def test_cache_clear(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    cache = ModelIRCache()
    compiler = sqlrules.Compiler(cache=True, model_cache=cache)
    compiler.compile_model(Filter)
    assert cache.get(Filter) is not None
    cache.clear()
    assert cache.get(Filter) is None


def test_diagnostics_warn_records_pattern(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(min_length=2, pattern=r"^A")]

    compiler = sqlrules.Compiler(on_unsupported="warn", cache=False)
    with pytest.warns(SQLRulesWarning, match="pattern"):
        rules = compiler.compile(Filter, items)

    assert len(rules["name"]) == 1
    assert len(compiler.diagnostics) == 1
    diag = compiler.diagnostics[0]
    assert diag.severity == "warning"
    assert diag.field == "name"
    assert diag.operator == "pattern"
    assert diag.value == PatternSpec(pattern=r"^A")
    assert diag.code == "unsupported_constraint"


def test_diagnostics_ignore_records_pattern(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    compiler = sqlrules.Compiler(on_unsupported="ignore", cache=False)
    assert compiler.compile(Filter, items) == {}
    assert len(compiler.diagnostics) == 1
    assert compiler.diagnostics[0].severity == "info"
    assert compiler.diagnostics[0].operator == "pattern"
    assert compiler.diagnostics[0].code == "unsupported_constraint"


def test_diagnostics_cleared_on_success(items: Table) -> None:
    class Bad(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    class Good(BaseModel):
        age: Annotated[int, Field(ge=18)]

    compiler = sqlrules.Compiler(on_unsupported="ignore", cache=False)
    compiler.compile(Bad, items)
    assert compiler.diagnostics
    compiler.compile(Good, items)
    assert compiler.diagnostics == ()


def test_pattern_extracted_as_ir_operator(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    compiler = sqlrules.Compiler(cache=False)
    model_ir = compiler.compile_model(Filter)
    assert model_ir.fields[0].constraints == (
        Constraint("name", "pattern", PatternSpec(pattern=r"^A")),
    )


def test_custom_pattern_translator(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    registry = default_registry()

    def pattern_translator(constraint, column, context):  # type: ignore[no-untyped-def]
        return column.op("~")(pattern_text(constraint.value)[0])

    registry.register("pattern", pattern_translator)
    compiler = sqlrules.Compiler(registry=registry, cache=False)
    rules = compiler.compile(Filter, items)
    assert len(rules["name"]) == 1
    compiled = str(rules["name"][0].compile(dialect=sqlite.dialect()))
    assert "~" in compiled


def test_uuid_literal_and_unconstrained(items: Table) -> None:
    uid = UUID("12345678-1234-5678-1234-567812345678")

    class Filter(BaseModel):
        id: Literal[uid]  # type: ignore[valid-type]
        name: UUID  # unconstrained → omitted

    rules = sqlrules.compile(Filter, items, cache=False)
    assert list(rules) == ["id"]
    assert len(rules["id"]) == 1


def test_uuid_rejects_numeric_constraints(items: Table) -> None:
    class Filter(BaseModel):
        id: Annotated[UUID, Field(ge=0)]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="ge"):
        sqlrules.compile(Filter, items, cache=False)


def test_time_range_constraints(items: Table) -> None:
    class Filter(BaseModel):
        starts: Annotated[time, Field(ge=time(9, 0), le=time(17, 0))]

    rules = sqlrules.compile(Filter, items, cache=False)
    assert list(rules) == ["starts"]
    assert len(rules["starts"]) == 2


def test_datetime_aware_no_conversion(items: Table) -> None:
    aware = datetime(2030, 1, 1, tzinfo=timezone.utc)

    class Filter(BaseModel):
        created: Annotated[datetime, Field(le=aware)]

    rules = sqlrules.compile(Filter, items, cache=False)
    expr = rules["created"][0]
    # Value is preserved as-is (no timezone conversion by SQLRules).
    assert expr.right.value == aware  # type: ignore[attr-defined]


def test_date_range_still_works(items: Table) -> None:
    table = Table("t", MetaData(), Column("born", String))

    class Filter(BaseModel):
        born: Annotated[date, Field(ge=date(2000, 1, 1))]

    # Column type is unrelated; expression still builds.
    rules = sqlrules.compile(Filter, table, cache=False)
    assert "born" in rules


def test_decimal_comparisons_and_multiple_of(items: Table) -> None:
    class Filter(BaseModel):
        score: Annotated[Decimal, Field(ge=Decimal("0"), multiple_of=Decimal("0.5"))]

    rules = sqlrules.compile(Filter, items, cache=False)
    assert len(rules["score"]) == 2


def test_decimal_precision_still_unsupported(items: Table) -> None:
    class Filter(BaseModel):
        score: Annotated[Decimal, Field(max_digits=5, decimal_places=2, ge=0)]

    with pytest.raises(UnsupportedConstraintError, match="max_digits|decimal_places"):
        sqlrules.compile(Filter, items, cache=False)


def test_module_compile_cache_flag(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    rules = sqlrules.compile(Filter, items, cache=False)
    assert "age" in rules


def test_temporal_multiple_of_rejected(items: Table) -> None:
    class DateFilter(BaseModel):
        created: Annotated[datetime, Field(multiple_of=1)]  # type: ignore[type-var]

    class TimeFilter(BaseModel):
        starts: Annotated[time, Field(multiple_of=1)]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        sqlrules.compile(DateFilter, items, cache=False)
    with pytest.raises(UnsupportedConstraintError, match="multiple_of"):
        sqlrules.compile(TimeFilter, items, cache=False)


def test_re_pattern_normalized_to_pattern_spec(items: Table) -> None:
    import re

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A"))]

    compiler = sqlrules.Compiler(cache=False)
    model_ir = compiler.compile_model(Filter)
    assert model_ir.fields[0].constraints == (
        Constraint("name", "pattern", PatternSpec(pattern=r"^A")),
    )


def test_re_pattern_ignore_case_preserved(items: Table) -> None:
    import re

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=re.compile(r"^A", re.I))]

    compiler = sqlrules.Compiler(cache=False)
    model_ir = compiler.compile_model(Filter)
    assert model_ir.fields[0].constraints == (
        Constraint("name", "pattern", PatternSpec(pattern=r"^A", ignore_case=True)),
    )


def test_invalid_pattern_type_rejected() -> None:
    from sqlrules.constraints import _normalize_pattern

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        _normalize_pattern("name", 123)


def test_validation_only_flags_ignored(items: Table) -> None:
    from pydantic import StringConstraints

    class StrFilter(BaseModel):
        name: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

    class FloatFilter(BaseModel):
        score: Annotated[float, Field(ge=0, allow_inf_nan=False)]

    assert "name" in sqlrules.compile(StrFilter, items, cache=False)
    assert "score" in sqlrules.compile(FloatFilter, items, cache=False)


def test_module_warn_attributes_outside_sqlrules(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sqlrules.compile(Filter, items, on_unsupported="warn", cache=False)

    assert caught
    path = caught[0].filename.replace("\\", "/")
    assert "/src/sqlrules/" not in path
    assert not path.endswith("/sqlrules/compiler.py")


def test_uuid_enum_and_length_reject(items: Table) -> None:
    class IdEnum(Enum):
        A = UUID("12345678-1234-5678-1234-567812345678")
        B = UUID("12345678-1234-5678-1234-567812345679")

    class EnumFilter(BaseModel):
        id: IdEnum

    rules = sqlrules.compile(EnumFilter, items, cache=False)
    assert "id" in rules

    class LenFilter(BaseModel):
        id: Annotated[UUID, Field(min_length=1)]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="min_length"):
        sqlrules.compile(LenFilter, items, cache=False)


def test_pattern_on_non_str_rejected(items: Table) -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(pattern=r"x")]  # type: ignore[type-var]

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        sqlrules.compile(Filter, items, cache=False)


def test_phase1_pattern_phase2_policy(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    model_ir = sqlrules.Compiler(cache=False).compile_model(Filter)
    assert model_ir.fields[0].constraints[0].operator == "pattern"

    with pytest.raises(UnsupportedConstraintError, match="pattern"):
        sqlrules.Compiler(on_unsupported="raise", cache=False).bind(model_ir, items)

    with pytest.warns(SQLRulesWarning, match="pattern"):
        assert sqlrules.Compiler(on_unsupported="warn", cache=False).bind(model_ir, items) == {}


def test_shared_default_cache_across_compilers(items: Table) -> None:
    from sqlrules.cache import default_cache

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    default_cache().clear()
    c1 = sqlrules.Compiler(cache=True)
    c2 = sqlrules.Compiler(cache=True)
    ir1 = c1.compile_model(Filter)
    ir2 = c2.compile_model(Filter)
    assert ir1 is ir2


def test_compile_model_clears_diagnostics(items: Table) -> None:
    class Bad(BaseModel):
        name: Annotated[str, Field(pattern=r"^A")]

    class Good(BaseModel):
        age: Annotated[int, Field(ge=18)]

    compiler = sqlrules.Compiler(on_unsupported="ignore", cache=False)
    compiler.compile(Bad, items)
    assert compiler.diagnostics
    compiler.compile_model(Good)
    assert compiler.diagnostics == ()


def test_constrained_time_missing_column_raises() -> None:
    table = Table("t", MetaData(), Column("other", Integer))

    class Filter(BaseModel):
        starts: Annotated[time, Field(ge=time(9, 0))]

    with pytest.raises(sqlrules.MissingColumnError):
        sqlrules.compile(Filter, table, cache=False)

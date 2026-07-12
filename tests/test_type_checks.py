"""Tests for emit_type_checks / TypeSpec IR extraction and bind-phase translation."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, Strict
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.schema import Table

import sqlrules
from assert_sql import assert_rules_sql
from sqlrules import Compiler, TypeSpec, type_spec
from sqlrules.cache import ModelIRCache
from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint
from sqlrules.translators import default_registry


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


def test_type_spec_helper() -> None:
    spec = TypeSpec(python_type=int, strict=True, allow_none=False)
    assert type_spec(spec) is spec


def test_type_spec_rejects_non_typespec() -> None:
    with pytest.raises(TypeError, match="TypeSpec"):
        type_spec("int")  # type: ignore[arg-type]


def test_default_omits_unconstrained_type_checks(users: Table) -> None:
    class Filter(BaseModel):
        age: int
        name: str

    rules = sqlrules.compile(Filter, users)
    assert rules == {}


def test_emit_type_checks_extracts_ir() -> None:
    class Filter(BaseModel):
        age: int
        name: str

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    by_field = {field.descriptor.name: field.constraints for field in model_ir.fields}
    assert len(by_field["age"]) == 1
    assert by_field["age"][0].operator == "type_check"
    age_spec = type_spec(by_field["age"][0].value)
    assert age_spec == TypeSpec(python_type=int, strict=False, allow_none=False)
    name_spec = type_spec(by_field["name"][0].value)
    assert name_spec.python_type is str


def test_emit_type_checks_with_other_constraints() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    ops = [c.operator for c in model_ir.fields[0].constraints]
    assert ops == ["ge", "type_check"]


def test_literal_and_enum_skip_type_check() -> None:
    class Filter(BaseModel):
        status: Literal["ACTIVE", "DISABLED"]
        kind: Status

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    by_field = {field.descriptor.name: field.constraints for field in model_ir.fields}
    assert [c.operator for c in by_field["status"]] == ["literal"]
    assert [c.operator for c in by_field["kind"]] == ["enum"]


def test_optional_sets_allow_none() -> None:
    class Filter(BaseModel):
        age: int | None = None

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    spec = type_spec(model_ir.fields[0].constraints[0].value)
    assert spec.allow_none is True
    assert spec.python_type is int


def test_field_strict_overrides_model_lax() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(strict=True)]
        other: Annotated[int, Strict()]

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    specs = {
        field.descriptor.name: type_spec(field.constraints[0].value) for field in model_ir.fields
    }
    assert specs["age"].strict is True
    assert specs["other"].strict is True


def test_model_config_strict() -> None:
    class Filter(BaseModel):
        model_config = ConfigDict(strict=True)
        age: int

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    assert type_spec(model_ir.fields[0].constraints[0].value).strict is True


def test_field_strict_false_overrides_model_strict() -> None:
    class Filter(BaseModel):
        model_config = ConfigDict(strict=True)
        age: int = Field(strict=False)

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    assert type_spec(model_ir.fields[0].constraints[0].value).strict is False


def test_strict_marker_not_emitted_as_operator() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Strict(), Field(ge=1)]

    # Without type checks, Strict must not become a fake IR operator.
    model_ir = Compiler(emit_type_checks=False, cache=False).compile_model(Filter)
    assert [c.operator for c in model_ir.fields[0].constraints] == ["ge"]


def test_cache_separates_emit_flag() -> None:
    cache = ModelIRCache()

    class Filter(BaseModel):
        age: int

    without = Compiler(emit_type_checks=False, cache=True, model_cache=cache).compile_model(Filter)
    with_checks = Compiler(emit_type_checks=True, cache=True, model_cache=cache).compile_model(
        Filter
    )
    assert without.fields[0].constraints == ()
    assert with_checks.fields[0].constraints[0].operator == "type_check"
    assert (
        Compiler(emit_type_checks=False, cache=True, model_cache=cache).compile_model(Filter)
        is without
    )
    assert (
        Compiler(emit_type_checks=True, cache=True, model_cache=cache).compile_model(Filter)
        is with_checks
    )


def test_module_compile_emit_type_checks_needs_translator(users: Table) -> None:
    class Filter(BaseModel):
        age: int

    with pytest.raises(UnsupportedConstraintError, match="type_check") as exc:
        sqlrules.compile(Filter, users, emit_type_checks=True, cache=False)
    assert exc.value.operator == "type_check"


def test_type_check_compiles_with_custom_translator(users: Table) -> None:
    """Bind-phase: type_check IR translates when a plugin/custom translator exists."""

    class Filter(BaseModel):
        age: Annotated[int, Field(ge=18)]
        name: str | None = None

    def type_check_translator(
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool]:
        spec = type_spec(constraint.value)
        label = f"{spec.python_type.__name__}:strict={spec.strict}:none={spec.allow_none}"
        return column.op("TYPE_IS")(label)

    registry = default_registry().copy()
    registry.register_constraint("type_check", type_check_translator, on_conflict="raise")
    rules = Compiler(
        registry=registry,
        emit_type_checks=True,
        cache=False,
    ).compile(Filter, users)

    assert_rules_sql(
        rules,
        {
            "age": [
                "users.age >= 18",
                "users.age TYPE_IS 'int:strict=False:none=False'",
            ],
            "name": ["users.name TYPE_IS 'str:strict=False:none=True'"],
        },
    )


def test_containers_skip_type_check() -> None:
    from sqlrules import JsonContains

    class Filter(BaseModel):
        meta: Annotated[dict[str, Any], JsonContains({"a": 1})]

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    ops = [c.operator for c in model_ir.fields[0].constraints]
    assert "type_check" not in ops
    assert "json_contains" in ops


def test_annotated_optional_allow_none() -> None:
    class Filter(BaseModel):
        age: Annotated[int, Field(ge=0)] | None = None

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    ops = [c.operator for c in model_ir.fields[0].constraints]
    assert "ge" in ops and "type_check" in ops
    type_c = next(c for c in model_ir.fields[0].constraints if c.operator == "type_check")
    assert type_spec(type_c.value).allow_none is True


def test_float_and_uuid_type_check_ir() -> None:
    from decimal import Decimal
    from uuid import UUID

    class Filter(BaseModel):
        amount: float
        price: Decimal
        id: UUID

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    by_name = {f.descriptor.name: type_spec(f.constraints[0].value) for f in model_ir.fields}
    assert by_name["amount"].python_type is float
    assert by_name["price"].python_type is Decimal
    assert by_name["id"].python_type is UUID


def test_string_constraints_strict_flag() -> None:
    from pydantic import StringConstraints

    class Filter(BaseModel):
        name: Annotated[str, StringConstraints(strict=True, min_length=2)]

    model_ir = Compiler(emit_type_checks=True, cache=False).compile_model(Filter)
    type_c = next(c for c in model_ir.fields[0].constraints if c.operator == "type_check")
    assert type_spec(type_c.value).strict is True
    # Length still extracts alongside type_check.
    ops = [c.operator for c in model_ir.fields[0].constraints]
    assert "min_length" in ops

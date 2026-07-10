"""Tests for emit_type_checks / TypeSpec IR extraction."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, Strict
from sqlalchemy.sql.schema import Table

import sqlrules
from sqlrules import Compiler, TypeSpec, type_spec
from sqlrules.cache import ModelIRCache
from sqlrules.errors import UnsupportedConstraintError
from sqlrules.ir import Constraint


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


def test_type_spec_helper() -> None:
    spec = TypeSpec(python_type=int, strict=True, allow_none=False)
    assert type_spec(spec) is spec


def test_type_spec_rejects_non_typespec() -> None:
    try:
        type_spec("int")
    except TypeError as exc:
        assert "TypeSpec" in str(exc)
    else:
        raise AssertionError("expected TypeError")


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
    # Re-fetch from cache
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

    try:
        sqlrules.compile(Filter, users, emit_type_checks=True, cache=False)
    except UnsupportedConstraintError as exc:
        assert exc.operator == "type_check"
    else:
        raise AssertionError("expected UnsupportedConstraintError")


def test_type_check_constraint_shape() -> None:
    constraint = Constraint(
        "age",
        "type_check",
        TypeSpec(python_type=int, strict=False, allow_none=True),
    )
    assert constraint.operator == "type_check"
    assert isinstance(constraint.value, TypeSpec)


def test_containers_skip_type_check() -> None:
    from typing import Any

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


def test_is_strict_marker_rejects_type_object() -> None:
    from sqlrules.constraints import _is_strict_marker, resolve_field_strict
    from sqlrules.ir import FieldDescriptor

    assert _is_strict_marker(Strict) is False
    descriptor = FieldDescriptor(
        name="age",
        alias=None,
        annotation=int,
        metadata=(),
    )
    assert resolve_field_strict(descriptor, model_strict=True) is True


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


def test_pattern_text_and_pattern_spec_helpers() -> None:
    from sqlrules.constraints import _normalize_pattern, pattern_text
    from sqlrules.ir import PatternSpec

    assert pattern_text("abc") == ("abc", False)
    assert pattern_text(PatternSpec("x", ignore_case=True)) == ("x", True)
    assert _normalize_pattern("f", PatternSpec("p")) == PatternSpec("p")


def test_enum_rejects_numeric_constraint() -> None:
    class Filter(BaseModel):
        kind: Annotated[Status, Field(ge=1)]

    try:
        Compiler(cache=False).compile_model(Filter)
    except UnsupportedConstraintError as exc:
        assert exc.operator == "ge"
    else:
        raise AssertionError("expected UnsupportedConstraintError")


def test_resolve_strict_from_plain_strict_attr() -> None:
    from sqlrules.constraints import (
        _is_constraint_marker,
        _unsupported_constraints,
        resolve_field_strict,
    )
    from sqlrules.ir import FieldDescriptor
    from sqlrules.markers import JsonContains

    class FakeStrict:
        def __init__(self) -> None:
            self.strict = True

    descriptor = FieldDescriptor(
        name="age",
        alias=None,
        annotation=int,
        metadata=(FakeStrict(),),
    )
    assert resolve_field_strict(descriptor, model_strict=False) is True
    assert _is_constraint_marker(JsonContains) is False
    assert _unsupported_constraints("m", JsonContains({"a": 1}))[0].operator == ("json_contains")
    assert _unsupported_constraints("m", object())[0].operator == "object"


def test_literal_rejects_length() -> None:
    class Filter(BaseModel):
        status: Annotated[Literal["A", "B"], Field(min_length=1)]

    try:
        Compiler(cache=False).compile_model(Filter)
    except UnsupportedConstraintError as exc:
        assert exc.operator == "min_length"
    else:
        raise AssertionError("expected UnsupportedConstraintError")

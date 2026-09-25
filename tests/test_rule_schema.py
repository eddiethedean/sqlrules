from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

import pytest
from annotated_types import MinLen
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveInt,
    StrictInt,
    StringConstraints,
    ValidationError,
    field_validator,
)
from pydantic import (
    Field as PydanticField,
)
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlrules_postgresql import PostgresPlugin

from sqlrules import (
    Compiler,
    Field,
    InvalidModelError,
    RuleConfig,
    RuleSchema,
    UnsupportedConstraintError,
    from_pydantic,
)


class Status(str, Enum):
    READY = "ready"
    PENDING = "pending"


def test_rule_schema_keeps_normal_pydantic_model_behavior() -> None:
    class UserRules(RuleSchema):
        id: PositiveInt
        age: int | None = PydanticField(ge=18, le=120)
        name: Annotated[str, StringConstraints(min_length=2, max_length=30)]
        status: Literal["ready", "pending"]

    user = UserRules.model_validate({"id": "12", "age": "21", "name": "Ada", "status": "ready"})
    assert user.id == 12
    assert user.model_dump() == {
        "id": 12,
        "age": 21,
        "name": "Ada",
        "status": "ready",
    }
    with pytest.raises(ValidationError):
        UserRules.model_validate({"id": 0, "age": None, "name": "A", "status": "ready"})

    app = FastAPI()

    def echo_user(payload):
        return payload

    echo_user.__annotations__ = {"payload": UserRules, "return": UserRules}
    app.post("/users")(echo_user)
    response = TestClient(app).post(
        "/users",
        json={"id": "12", "age": "21", "name": "Ada", "status": "ready"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 12


def test_supported_pydantic_metadata_and_strict_aliases_normalize() -> None:
    class Rules(RuleSchema):
        model_config = ConfigDict(strict=True)

        count: int = PydanticField(strict=False, ge=0)
        label: Annotated[str, MinLen(2)]
        fixed: StrictInt

    schema = Compiler().compile_model(Rules)
    assert [(field.name, field.strict) for field in schema.fields] == [
        ("count", False),
        ("label", True),
        ("fixed", True),
    ]
    assert schema.fields[0].constraints[0].operator == "ge"
    assert Rules.model_validate({"count": "1", "label": "ab", "fixed": 1})
    with pytest.raises(ValidationError):
        Rules.model_validate({"count": "1", "label": "ab", "fixed": "1"})


def test_scalar_and_domain_annotations_compile_for_postgresql() -> None:
    class Scalars(RuleSchema):
        flag: bool
        count: int
        ratio: float
        amount: Decimal
        title: str
        day: date
        created: datetime
        at: time
        token: UUID
        status: Status

    table = Table(
        "scalars",
        MetaData(),
        Column("flag", Boolean),
        Column("count", Integer),
        Column("ratio", Float),
        Column("amount", Numeric),
        Column("title", String),
        Column("day", Date),
        Column("created", DateTime),
        Column("at", Time),
        Column("token", PostgreSQLUUID),
        Column("status", String(collation="C")),
    )
    compiled = Compiler(plugins=[PostgresPlugin()]).compile(Scalars, table)
    assert len(compiled.fields) == 10
    assert compiled.backend == "postgresql"


def test_sqlrules_column_metadata_is_separate_from_pydantic_aliases() -> None:
    class Rules(RuleSchema):
        display_name: str = Field(column="display", alias="displayName", min_length=2)

    value = Rules.model_validate({"displayName": "Ada"})
    assert value.display_name == "Ada"
    field = Compiler().compile_model(Rules).fields[0]
    assert field.column == "display"
    assert field.alias == "displayName"


def test_single_inheritance_preserves_order_and_empty_requires_opt_in() -> None:
    class Parent(RuleSchema):
        first: int

    class Child(Parent):
        second: str

    assert [field.name for field in Compiler().compile_model(Child).fields] == [
        "first",
        "second",
    ]

    class Empty(RuleSchema):
        __rule_config__ = RuleConfig(allow_empty=True)

    assert Compiler().compile_model(Empty).allow_empty


def test_unrestricted_pydantic_model_is_rejected_by_compiler() -> None:
    class Request(BaseModel):
        age: int

    with pytest.raises(InvalidModelError, match="from_pydantic"):
        Compiler().compile_model(Request)  # type: ignore[arg-type]


def test_unsupported_declarations_fail_at_class_creation() -> None:
    with pytest.raises(TypeError, match="min_length"):

        class InvalidConstraint(RuleSchema):
            count: Annotated[int, PydanticField(min_length=1)]

    with pytest.raises(TypeError, match="metadata"):

        class InvalidMetadata(RuleSchema):
            name: Annotated[str, object()]

    with pytest.raises(TypeError, match="field_validators"):

        class ValidatorRules(RuleSchema):
            age: int

            @field_validator("age")
            @classmethod
            def positive(cls, value: int) -> int:
                return abs(value)

    with pytest.raises(TypeError, match="multiple_inheritance"):

        class Left(RuleSchema):
            left: int

        class Right(RuleSchema):
            other: int

        class MultipleInheritance(Left, Right):
            pass


def test_from_pydantic_drops_incompatible_features_and_reports_them() -> None:
    class Request(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        user_id: int = PydanticField(default=4, alias="userId", ge=1)
        payload: bytes

        @field_validator("user_id")
        @classmethod
        def clamp(cls, value: int) -> int:
            return max(value, 1)

    with pytest.warns(UserWarning, match="changed behavior"):
        conversion = from_pydantic(Request, on_incompatible="warn")
    assert tuple(conversion.model.model_fields) == ("user_id",)
    assert conversion.model.model_fields["user_id"].alias == "userId"
    assert conversion.model().user_id == 4
    assert conversion.model.model_validate({"userId": "7"}).user_id == 7
    assert any(item.reason_code == "unsupported_field_type" for item in conversion.report.entries)
    assert any(item.reason_code == "python_callback_removed" for item in conversion.report.entries)
    assert any(item.reason_code == "model_config_not_copied" for item in conversion.report.entries)
    assert any(item.reason_code == "field_aliases_preserved" for item in conversion.report.entries)
    converted_schema = Compiler().compile_model(conversion.model)
    assert converted_schema.provenance == (
        f"from_pydantic:{Request.__module__}.{Request.__qualname__}"
    )
    assert converted_schema.fields[0].source_location.endswith(".user_id")

    app = FastAPI()

    def echo_converted(payload):
        return payload

    echo_converted.__annotations__ = {
        "payload": conversion.model,
        "return": conversion.model,
    }
    app.post("/converted")(echo_converted)
    response = TestClient(app).post("/converted", json={"userId": "9"})
    assert response.status_code == 200
    assert response.json()["userId"] == 9

    with pytest.raises(UnsupportedConstraintError, match="remove or change"):
        from_pydantic(Request, on_incompatible="raise")


def test_from_pydantic_does_not_run_default_factories_during_conversion() -> None:
    calls = 0

    def make_default() -> int:
        nonlocal calls
        calls += 1
        return 3

    class Request(BaseModel):
        count: int = PydanticField(default_factory=make_default)

    converted = from_pydantic(Request, on_incompatible="drop")
    assert calls == 0
    assert converted.model().count == 3
    assert calls == 1


def test_empty_conversion_requires_allow_empty() -> None:
    class Request(BaseModel):
        payload: bytes

    with pytest.raises(UnsupportedConstraintError, match="allow_empty"):
        from_pydantic(Request, on_incompatible="drop")
    conversion = from_pydantic(Request, on_incompatible="drop", allow_empty=True)
    assert conversion.report.allow_empty
    assert not conversion.model.model_fields

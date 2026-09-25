from __future__ import annotations

import re
from enum import Flag, IntFlag
from typing import Annotated, Literal

import pytest
from pydantic import ConfigDict, Field, StringConstraints

from sqlrules import Compiler, InvalidModelError, RuleSchema, from_pydantic


def test_pattern_flags_and_string_transform_metadata_are_checked() -> None:
    class PatternRules(RuleSchema):
        name: Annotated[str, Field(pattern=re.compile(r"^ada", re.IGNORECASE))]

    constraint = Compiler().compile_model(PatternRules).fields[0].constraints[0]
    assert constraint.operator == "pattern"
    assert constraint.value.pattern == "^ada"
    assert constraint.value.ignore_case

    with pytest.raises(TypeError, match="VERBOSE"):

        class VerbosePatternRules(RuleSchema):
            name: Annotated[str, Field(pattern=re.compile("^ada", re.VERBOSE))]

    with pytest.raises(TypeError, match="metadata"):

        class NormalizedStrings(RuleSchema):
            name: Annotated[str, StringConstraints(strip_whitespace=True)]


def test_incompatible_model_config_and_constraint_combinations_are_rejected() -> None:
    with pytest.raises(TypeError, match="model_config"):

        class NormalizingModel(RuleSchema):
            model_config = ConfigDict(str_to_lower=True)
            name: str

    with pytest.raises(TypeError, match="multiple_of"):

        class InvalidDivisor(RuleSchema):
            count: Annotated[int, Field(multiple_of=0)]

    with pytest.raises(TypeError, match="bounds"):

        class EmptyInterval(RuleSchema):
            count: Annotated[int, Field(gt=5, le=5)]

    with pytest.raises(TypeError, match="length"):

        class InvalidLength(RuleSchema):
            name: Annotated[str, Field(min_length=5, max_length=2)]


def test_literal_and_enum_domains_require_one_supported_scalar_type() -> None:
    with pytest.raises(TypeError, match="Literal"):

        class MixedLiteral(RuleSchema):
            value: Literal[1, "one"]

    class CombinedFlags(Flag):
        READ = 1
        WRITE = 2

    class CombinedIntFlags(IntFlag):
        READ = 1
        WRITE = 2

    with pytest.raises(TypeError, match="enum"):

        class FlagRules(RuleSchema):
            value: CombinedFlags

    with pytest.raises(TypeError, match="enum"):

        class IntFlagRules(RuleSchema):
            value: CombinedIntFlags


def test_conversion_of_existing_rule_schema_and_argument_errors() -> None:
    class ExistingRules(RuleSchema):
        value: int

    converted = from_pydantic(ExistingRules)
    assert converted.model is ExistingRules
    assert not converted.report.has_incompatibilities

    with pytest.raises(InvalidModelError, match="SQLRules RuleSchema"):
        from_pydantic(dict)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="on_incompatible"):
        from_pydantic(ExistingRules, on_incompatible="invalid")  # type: ignore[arg-type]

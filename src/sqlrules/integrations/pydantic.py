from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, create_model
from pydantic_core import PydanticUndefined

from sqlrules.errors import InvalidModelError, UnsupportedConstraintError
from sqlrules.models import (
    RuleConfig,
    RuleSchema,
    _domain_type,
    _metadata_values,
    _recognized_metadata,
    _unwrap,
    normalize_schema,
)

ConversionPolicy = Literal["warn", "drop", "raise"]
_dynamic_create_model = cast(Any, create_model)


@dataclass(frozen=True, slots=True)
class ConversionEntry:
    """One deterministic explanation of a preserved, changed, or dropped feature."""

    location: str
    feature: str
    reason_code: str
    outcome: Literal["preserved", "metadata", "dropped", "changed"]
    behavior: Literal["same", "broader", "narrower", "unknown"]
    reason: str


@dataclass(frozen=True, slots=True)
class ConversionReport:
    source_model: str
    target_model: str
    entries: tuple[ConversionEntry, ...]
    allow_empty: bool

    @property
    def has_incompatibilities(self) -> bool:
        return any(item.outcome in {"dropped", "changed"} for item in self.entries)


@dataclass(frozen=True, slots=True)
class PydanticConversion:
    model: type[RuleSchema]
    report: ConversionReport


def _model_name(model: type[Any]) -> str:
    return f"{model.__module__}.{model.__qualname__}"


def _decorator_features(model: type[BaseModel]) -> list[tuple[str, str]]:
    decorators = getattr(model, "__pydantic_decorators__", None)
    if decorators is None:
        return []
    result: list[tuple[str, str]] = []
    for name in ("field_validators", "model_validators", "field_serializers", "model_serializers"):
        entries = getattr(decorators, name, {}) or {}
        result.extend((name, str(item)) for item in entries)
    computed = getattr(decorators, "computed_fields", {}) or {}
    result.extend(("computed_fields", str(item)) for item in computed)
    return result


def _report_entry(
    location: str,
    feature: str,
    code: str,
    outcome: Literal["preserved", "metadata", "dropped", "changed"],
    behavior: Literal["same", "broader", "narrower", "unknown"],
    reason: str,
) -> ConversionEntry:
    return ConversionEntry(location, feature, code, outcome, behavior, reason)


def from_pydantic(
    model: type[BaseModel],
    *,
    on_incompatible: ConversionPolicy = "warn",
    allow_empty: bool = False,
) -> PydanticConversion:
    """Convert a full Pydantic v2 model into the SQLRules-supported subset.

    The source class is never modified. Validators, serializers, unsupported
    fields, and metadata are reported and removed from the generated model.
    Defaults and default factories are copied as declarations and are never
    executed during conversion.
    """
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise InvalidModelError(model=model)
    if on_incompatible not in {"warn", "drop", "raise"}:
        raise ValueError("on_incompatible must be 'warn', 'drop', or 'raise'")

    entries: list[ConversionEntry] = []
    source_name = _model_name(model)

    if issubclass(model, RuleSchema):
        schema = normalize_schema(model)
        entries.append(
            _report_entry(
                source_name,
                "RuleSchema declarations",
                "already_rules_schema",
                "preserved",
                "same",
                "The source model already satisfies the SQLRules declaration subset.",
            )
        )
        return PydanticConversion(
            model=model,
            report=ConversionReport(source_name, source_name, tuple(entries), schema.allow_empty),
        )

    converted_fields: dict[str, tuple[Any, Any]] = {}
    for name, info in model.model_fields.items():
        location = f"{source_name}.{name}"
        concrete, _, annotation_metadata = _unwrap(info.annotation)
        try:
            _domain_type(concrete, name)
        except UnsupportedConstraintError as exc:
            entries.append(
                _report_entry(
                    location,
                    repr(info.annotation),
                    "unsupported_field_type",
                    "dropped",
                    "unknown",
                    str(exc),
                )
            )
            continue

        metadata = _metadata_values(info, annotation_metadata)
        supported_metadata = [item for item in metadata if _recognized_metadata(item)]
        unsupported_metadata = [item for item in metadata if not _recognized_metadata(item)]
        for item in unsupported_metadata:
            behavior: Literal["broader", "narrower", "unknown"] = (
                "broader"
                if type(item).__name__ in {"Gt", "Ge", "Lt", "Le", "MinLen", "MaxLen"}
                else "unknown"
            )
            entries.append(
                _report_entry(
                    location,
                    type(item).__name__,
                    "unsupported_metadata",
                    "dropped",
                    behavior,
                    "The metadata has no supported SQLRules representation and was removed.",
                )
            )

        candidate_metadata = list(supported_metadata)
        clean_info: Any
        field_is_supported = False
        normalized_probe = None
        while True:
            clean_info = copy.copy(info)
            clean_info.metadata = list(candidate_metadata)
            try:
                probe = _dynamic_create_model(
                    f"_{model.__name__}_{name}_Probe",
                    __base__=RuleSchema,
                    __module__=model.__module__,
                    **{name: (info.annotation, clean_info)},
                )
                normalized_probe = normalize_schema(probe)
                field_is_supported = True
                break
            except (TypeError, UnsupportedConstraintError, ValueError) as exc:
                if candidate_metadata:
                    dropped = candidate_metadata.pop()
                    entries.append(
                        _report_entry(
                            location,
                            type(dropped).__name__,
                            "incompatible_constraint_dropped",
                            "dropped",
                            "broader",
                            str(exc),
                        )
                    )
                    continue
                entries.append(
                    _report_entry(
                        location,
                        "field declaration",
                        "invalid_rule_declaration",
                        "dropped",
                        "unknown",
                        str(exc),
                    )
                )
                break
        if not field_is_supported:
            continue

        converted_fields[name] = (info.annotation, clean_info)
        entries.append(
            _report_entry(
                location,
                "field type and supported constraints",
                "field_preserved",
                "preserved",
                "same",
                "The field's supported scalar type and SQL-translatable constraints were retained.",
            )
        )
        if normalized_probe is not None:
            normalized_field = normalized_probe.fields[0]
            for constraint in normalized_field.constraints:
                entries.append(
                    _report_entry(
                        location,
                        f"{constraint.operator}={constraint.value!r}",
                        "constraint_preserved",
                        "preserved",
                        "same",
                        "The SQL-translatable field constraint was retained.",
                    )
                )
        aliases = tuple(
            dict.fromkeys(
                alias
                for alias in (info.alias, info.validation_alias, info.serialization_alias)
                if isinstance(alias, str)
            )
        )
        if aliases:
            entries.append(
                _report_entry(
                    location,
                    f"aliases={aliases!r}",
                    "field_aliases_preserved",
                    "metadata",
                    "same",
                    "Pydantic validation and serialization aliases were retained; "
                    "they do not change SQL column binding.",
                )
            )
        if info.default is not PydanticUndefined or info.default_factory is not None:
            entries.append(
                _report_entry(
                    location,
                    "default or default_factory",
                    "field_default_preserved",
                    "metadata",
                    "same",
                    "The declaration was copied for Pydantic model use and was not "
                    "executed during conversion.",
                )
            )
        has_descriptive_metadata = any(
            getattr(info, name, None) is not None for name in ("title", "description")
        ) or bool(getattr(info, "examples", None))
        if has_descriptive_metadata:
            entries.append(
                _report_entry(
                    location,
                    "title, description, or examples",
                    "descriptive_metadata_preserved",
                    "metadata",
                    "same",
                    "Descriptive Pydantic metadata was retained on the generated field.",
                )
            )

    for feature, name in _decorator_features(model):
        entries.append(
            _report_entry(
                f"{source_name}.{name}",
                feature,
                "python_callback_removed",
                "changed",
                "unknown",
                "Python callbacks and computed fields are not executed or "
                "translated into SQL rules.",
            )
        )

    source_config = dict(model.model_config)
    strict = bool(source_config.pop("strict", False))
    if source_config:
        entries.append(
            _report_entry(
                source_name,
                "Pydantic model_config",
                "model_config_not_copied",
                "changed",
                "unknown",
                "Only Pydantic strictness is retained as a SQLRules validation "
                "setting; other config behavior remains on the source model.",
            )
        )
    converted_base = type(
        f"_{model.__name__}RuleSchemaBase",
        (RuleSchema,),
        {
            "__module__": model.__module__,
            "__rule_config__": RuleConfig(allow_empty=True),
            "__sqlrules_provenance__": f"from_pydantic:{source_name}",
            "model_config": ConfigDict(strict=strict),
        },
    )
    type.__setattr__(converted_base, "__rule_config__", RuleConfig(allow_empty=allow_empty))

    if not converted_fields and not allow_empty:
        entries.append(
            _report_entry(
                source_name,
                "empty converted schema",
                "empty_conversion_rejected",
                "dropped",
                "unknown",
                "No SQL-compatible fields remain; pass allow_empty=True to "
                "permit an always-true predicate.",
            )
        )
        report = ConversionReport(source_name, "", tuple(entries), False)
        raise UnsupportedConstraintError(
            model.__name__,
            "empty_conversion",
            report,
            "No SQL-compatible fields remain. Pass allow_empty=True to "
            "explicitly allow an empty rules model.",
        )

    target_name = f"{model.__name__}Rules"
    converted_model = _dynamic_create_model(
        target_name,
        __base__=converted_base,
        __module__=model.__module__,
        **converted_fields,
    )
    normalize_schema(converted_model)
    entries.sort(key=lambda item: (item.location, item.reason_code, item.feature))
    report = ConversionReport(
        source_name, _model_name(converted_model), tuple(entries), allow_empty
    )

    if on_incompatible == "raise" and report.has_incompatibilities:
        raise UnsupportedConstraintError(
            model.__name__,
            "pydantic_conversion",
            report,
            "Conversion would remove or change source-model behavior. Use "
            "'drop' to inspect the report or 'warn' to convert with warnings.",
        )
    if on_incompatible == "warn" and report.has_incompatibilities:
        summary = "; ".join(
            f"{item.location}: {item.reason_code} ({item.behavior})"
            for item in report.entries
            if item.outcome in {"dropped", "changed"}
        )
        warnings.warn(
            f"Pydantic model conversion to {target_name} changed behavior: {summary}",
            UserWarning,
            stacklevel=2,
        )
    return PydanticConversion(converted_model, report)


__all__ = [
    "ConversionEntry",
    "ConversionPolicy",
    "ConversionReport",
    "PydanticConversion",
    "from_pydantic",
]

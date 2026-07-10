"""Dialect-oriented constraint markers for Annotated metadata.

Markers are extracted into IR as ``Constraint(field, marker.operator, marker.value)``.
Core does not translate these operators; dialect plugins register translators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConstraintMarker(Protocol):
    """Protocol for Annotated metadata that becomes a SQLRules IR constraint."""

    operator: str
    value: Any


@dataclass(frozen=True, slots=True)
class JsonContains:
    """Require JSON/JSONB containment (``json_contains``)."""

    value: Any
    operator: str = field(default="json_contains", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class JsonHasKey:
    """Require a JSON object key (``json_has_key``)."""

    value: Any
    operator: str = field(default="json_has_key", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class ArrayContains:
    """Require array containment (``array_contains``)."""

    value: Any
    operator: str = field(default="array_contains", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class ArrayOverlap:
    """Require array overlap (``array_overlap``)."""

    value: Any
    operator: str = field(default="array_overlap", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class RangeContains:
    """Require range containment (``range_contains``)."""

    value: Any
    operator: str = field(default="range_contains", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class RangeOverlap:
    """Require range overlap (``range_overlap``)."""

    value: Any
    operator: str = field(default="range_overlap", init=False, repr=False)


@dataclass(frozen=True, slots=True)
class FullTextMatch:
    """Require a full-text match (``fulltext_match``)."""

    value: Any
    operator: str = field(default="fulltext_match", init=False, repr=False)


__all__ = [
    "ArrayContains",
    "ArrayOverlap",
    "ConstraintMarker",
    "FullTextMatch",
    "JsonContains",
    "JsonHasKey",
    "RangeContains",
    "RangeOverlap",
]

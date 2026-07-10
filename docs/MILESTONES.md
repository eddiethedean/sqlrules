# SQLRules Milestones

## Vision

SQLRules should become the canonical compiler that transforms supported
Pydantic constraints into reusable SQLAlchemy WHERE expressions.

Each milestone delivers a complete, usable release.

------------------------------------------------------------------------

# 0.1.0 --- Foundation (MVP)

## Goals

-   Establish the compiler architecture
-   Publish the first stable public API
-   Support the most common constraints

## Features

### Compiler

-   `compile(model, table)`
-   Deterministic output
-   Rule dictionary

### Constraint Support

-   gt
-   ge
-   lt
-   le
-   multiple_of
-   min_length
-   max_length
-   Literal
-   Enum

### Core Components

-   Model inspector
-   Constraint extractor
-   Translator registry
-   Rule assembler

### Documentation

-   README
-   SPEC
-   API
-   Architecture
-   Design documents

### Quality

-   95% unit test coverage

-   Type checking

-   CI

-   Semantic versioning

Deliverable:

``` python
rules = sqlrules.compile(UserFilter, users)
```

------------------------------------------------------------------------

# 0.2.0 --- Compiler Maturity ✅

## Goals

Improve correctness and extensibility.

## Features

-   UUID support
-   date/time improvements (`time` + datetime polish)
-   regex IR (`pattern` extracted; no portable core translator)
-   structured diagnostics
-   metadata caching
-   benchmark suite

### Internal

-   immutable IR (`ModelIR` / `FieldIR`)
-   two-phase compilation
-   compiler context + diagnostics collector

------------------------------------------------------------------------

# 0.3.0 --- Plugin System ✅

## Goals

Open SQLRules for extension.

### Features

-   translator plugins
-   dialect plugins
-   registry API
-   plugin conformance tests
-   versioned plugin API

Official plugin packages begin:

-   sqlrules-postgresql
-   sqlrules-sqlite

------------------------------------------------------------------------

# 0.4.0 --- Dialect Enhancements ✅

## Goals

Provide optimized translations for major databases.

### PostgreSQL

-   regex (`~` / `~*`)
-   JSONB
-   ARRAY
-   range operators

### SQLite

-   REGEXP integration (`register_regexp`)
-   JSON helpers

### MySQL / MariaDB

-   JSON operators
-   full-text helpers

### SQL Server

-   JSON support
-   string optimizations (`LEN`)

### Core

-   `ConstraintMarker` + `sqlrules.markers`
-   `PatternSpec` for pattern IR
-   `list` / `dict` type support for marker fields

------------------------------------------------------------------------

# Post-1.0 — Performance (formerly 0.5)

## Goals

Optimize compilation after the 1.0 API freeze.

### Features

-   persistent metadata cache (optional)
-   optimized translator dispatch
-   allocation reductions
-   concurrent-safe caches
-   performance regression CI

Target:

-   Medium model compile \< 2 ms

------------------------------------------------------------------------

# Post-1.0 — Developer Experience (formerly 0.6)

## Goals

Make SQLRules pleasant to use.

### Features

-   richer error messages
-   IDE-friendly exceptions
-   helper utilities
-   improved documentation
-   migration guides
-   examples repository

------------------------------------------------------------------------

# Post-1.0 — Ecosystem examples (formerly 0.7)

Optional documentation/examples only — not product integrations:

-   SQLModel / FastAPI / Alembic usage notes
-   datamodel-code-generator examples

------------------------------------------------------------------------

# Post-1.0 — Advanced Constraints (formerly 0.8)

Potential features (only with deterministic SQL semantics):

-   decimal precision
-   contains / starts_with / ends_with
-   configurable null policies

------------------------------------------------------------------------

# Pre-1.0 — Contract hardening (replaces 0.9 RC theater)

API freeze activities happen as a short hardening cycle before tagging
1.0.0 — not a separate feature release:

-   bug fixing
-   documentation polish (Application / Plugin / Internal tiers)
-   compatibility verification
-   coordinated core + dialect plugin releases

No new major features.

------------------------------------------------------------------------

# 1.0.0 --- Stable Release

## Success Criteria

-   Stable Application API
-   Stable Plugin API (`PLUGIN_API_VERSION`)
-   Excellent documentation
-   Comprehensive test suite
-   Official dialect plugins released with core
-   Predictable compiler behavior

### Public API

-   compile()
-   where() / flatten()
-   Compiler
-   Plugin API exports (`TranslatorRegistry`, `pattern_text`, markers, …)

### Supported Platforms

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

------------------------------------------------------------------------

# Post-1.0 Ideas

-   Opt-in `emit_type_checks` / `TypeSpec` type-annotation WHERE rules
    (strict/lax approximations via dialect plugins)
-   Rust acceleration for metadata extraction
-   optional IR serialization
-   code generation helpers
-   static analysis integrations
-   additional official dialect plugins

------------------------------------------------------------------------

# Guiding Principles

Every release should:

-   remain focused
-   avoid feature creep
-   preserve deterministic behavior
-   maintain backward compatibility where promised
-   keep SQLRules a compiler rather than a query builder

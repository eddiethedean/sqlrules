# SQLRules Milestones

## Vision

SQLRules should compile its own rule schemas into reusable SQLAlchemy WHERE
expressions. Pydantic models can be converted explicitly into those schemas.

Each milestone delivers a complete, usable release.

------------------------------------------------------------------------

## 0.1.0 --- Foundation (MVP)

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

## 0.2.0 --- Compiler Maturity ✅

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

## 0.3.0 --- Plugin System ✅

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

## 0.4.0 --- Dialect Enhancements ✅

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

## Pre-1.0 — Contract hardening (replaces 0.9 RC theater)

API freeze activities happen as a short hardening cycle before tagging
1.0.0 — not a separate feature release:

-   bug fixing
-   documentation polish (Application / Plugin / Internal tiers)
-   compatibility verification
-   coordinated core + dialect plugin releases

No new major features.

------------------------------------------------------------------------

## 1.0.0 --- Stable Release ✅

### Success Criteria

-   Stable Application API
-   Stable Plugin API (`PLUGIN_API_VERSION`)
-   Opt-in `emit_type_checks` / `TypeSpec` (plugin-translated)
-   Documentation suitable for public adoption
-   Comprehensive test suite
-   Official dialect plugins released with core
  (`postgresql`, `sqlite`, `mysql`, `mssql`)
-   Predictable compiler behavior

### Public API

-   compile()
-   where() / flatten()
-   Compiler
-   `emit_type_checks` / `type_spec` / `TypeSpec`
-   Plugin API exports (`TranslatorRegistry`, `pattern_text`, markers, …)

### Supported Platforms

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

------------------------------------------------------------------------

## 2.x Release Policy

Status: planned. The [2.0 design](V2_DESIGN.md) defines the proposed API and
semantic contract. Phase 2.0 ends with **2.0.0**, phase 2.1 with **2.1.0**, and
so on. Internal work packages below are dependency steps within a release.
Dates are assigned after each phase's capability and conformance scope is fixed.

Core and the four official dialect packages stay in lockstep. Core already
depends on Pydantic v2; the conversion helper ships in the core distribution.
2.0 contains the breaking API and plugin changes; later phases add capabilities
while preserving the 2.0 semantic profile for existing schemas. Additional
coercions that broaden accepted data require an explicit opt-in or profile.

## 2.0.0 — Rule Schemas and Semantic Foundations (planned)

### Outcome

A complete SQLRules-owned Pydantic model workflow: declare or convert a model,
instantiate and validate it with normal Pydantic APIs, use it as a FastAPI
request or response model, then bind its SQL-compatible declarations with an
explicit backend and use the complete predicate in a SQLAlchemy query. Type-only
fields, lax coercion, strict mode, nullable constraints, and conversion reports
are required in this first release.

### Work package A — Freeze semantics and backend commitments

- Specify the SQLRules logical types, conversion table, strictness precedence,
  literal/enum domains, nullable truth tables, and root negation semantics in
  the design document.
- Distinguish a known data mismatch (false) from unsupported implementation
  capability (compile error). Capture observed storage types, numeric limits,
  decimal precision, time zones, string behavior, and database settings.
- Freeze supported server versions and a useful minimum capability matrix for
  PostgreSQL, SQLite, MySQL, and SQL Server. Require each backend's native scalar
  baseline where observable, nullable constraints, existing applicable operators,
  and a named set of useful coercions. Record emulated/unavailable types explicitly.
- Establish a reference semantic corpus and pin the Pydantic versions used for
  comparison. Record deliberate differences, including strict logical matching.

Exit: the matrix and expected acceptance cases are reviewed before finalizing
backend implementations. Existing regex-only type approximations do not count
as proof of conversion correctness.

### Work package B — Own declarations and conversion

Depends on A's schema semantics; can proceed alongside the backend prototypes.

- Implement `RuleSchema`, `Field`, `RuleConfig`, `Annotated` aliases, single
  inheritance, explicit column mapping, and immutable normalized schemas.
  `RuleSchema` subclasses Pydantic `BaseModel` and supports normal construction,
  `model_validate()`, `model_dump()`, and FastAPI use. Its class construction
  rejects field types, constraints, and custom validation behavior that cannot
  be represented as SQL rules. Once constructed, the model can be used anywhere
  a Pydantic model is accepted; SQLRules does not restrict application usage.
- Normalize Pydantic `FieldInfo`, `ConfigDict`, strict/constrained aliases,
  `Annotated` metadata, and compatible `annotated_types` constraints through a
  documented allowlist. Do not require `sqlrules.Field` for ordinary Pydantic
  constraints. Keep SQLRules helpers for SQL-only metadata and config.
- Resolve annotations before schema finalization and reject unsupported types,
  metadata, field options, and incompatible type/constraint pairs.
- Preserve title, description, and examples as metadata from the beginning.
- Implement `from_pydantic()` with warn/drop/raise policies and a report of
  preserved rules, metadata, dropped features, and changed/unknown semantics.
- Preserve type-only fields and strictness. Do not execute Python validators,
  default factories, or serializers to infer SQL. Require explicit opt-in for
  an empty converted schema and for mapping Pydantic aliases to database columns.
- Keep unrestricted Pydantic models usable in application code; require the
  converter before compiling one, and produce an actionable error if callers
  pass a plain `BaseModel` directly to the compiler.

Exit: native and converted schemas share one representation; conversion retains
provenance and returns a usable `RuleSchema` model class. Its report names every
source-model behavior removed or changed by conversion; parity with discarded
validators is not promised.

### Work package C — Compiler IR and result contract

Depends on A; integrates the schema representation from B.

- Build typed expression nodes and boolean grouping internally in 2.0.
  Nullable fields and domain constraints must already use complete groups.
- Introduce prepared values carrying source/null identity, a safe normalized
  expression, and a non-null validity predicate. Constraint translators consume
  the normalized expression.
- Return `CompiledRules` with one authoritative predicate, ordered field
  information, per-result diagnostics, and a structured `explain()` plan.
  `where(compiled)` returns `[compiled.predicate]` and `notwhere(compiled)`
  returns `[~compiled.predicate]`; both work with the existing spread-style
  `.where(*...)` call. `flatten(compiled)` remains an alias for `where()`.
- Freeze registry snapshots, isolate per-call state, and bound schema caches.
  Avoid retaining tables or stale mutable metadata in cached schema IR.
- Define plugin API v2 with source preparation, capability declarations,
  and constraint translation. Require an explicit backend provider.

Exit: the compiler can express null grouping and future model-level rules
without changing the result API in 2.1. Invalid data produces total boolean
predicates and compilation state is safe to share as documented.

### Work package D — Execute safe dialect translations

Depends on A and C; prototypes should begin early enough to refine the matrix.

- Implement the frozen matrix in all four official plugins. Use runtime type
  evidence where storage permits mixed types; no SQLite affinity-only shortcut.
- Prove that supported conversions are safe for malformed and out-of-range
  values, even when the database optimizer reorders predicate evaluation.
- Exercise type-only fields, numeric comparisons after coercion, strict
  mismatches, nullable bounds, literal/enum membership, and dialect markers.
- Prove that `where(compiled)` and `notwhere(compiled)` partition test rows
  exactly: required and optional SQL NULLs, malformed values, failed
  conversions, and explicitly allowed empty schemas each appear on one side
  only.
- Declare server-version requirements, database setting assumptions, and any
  connection helpers in capabilities and compiled plans.

Exit: real database execution confirms accepted row sets and conversion safety
for every advertised matrix entry. Unsupported entries produce stable, useful
errors. SQL rendering assertions supplement execution coverage.

### Work package E — Migration and coordinated 2.0.0 release

Depends on B, C, and D passing their gates.

- Document migration from direct Pydantic inputs, rule dictionaries,
  `emit_type_checks`, and the old optional dialect hint behavior. Preserve the
  list-returning `where()` call shape; show `notwhere()` and direct
  `~compiled.predicate` usage.
- Update API/IR/plugin contracts, README, runnable examples, support matrices,
  and release tooling for plugin API v2 and package pins `>=2,<3`.
- Establish cold/warm compilation performance baselines and regression budgets;
  exercise concurrency, cache limits, wheel imports, the converter, and
  FastAPI request/response integration.
- Run lint, typing, database conformance, documentation builds, and coordinated
  core/plugin package checks. Demonstrate the full declaration and conversion
  paths in the migration guide.
- Verify Pydantic-imported declarations, FastAPI request/response use, and
  converter warnings against the pinned Pydantic v2 release.

Release gate: all five packages are ready to publish as **2.0.0**. The default
scalar, strict/lax, nullable, adapter, and result contracts are complete; later
phases are not prerequisites for a useful 2.0 release.

## 2.1.0 — Public Rule Composition (planned)

Depends on the grouped IR, prepared values, and result contract from 2.0.

- Expose all/any/not composition and typed field references for cross-field
  conditions such as `end >= start`.
- Add scalar unions as branch-local type/coercion/constraint groups. Define
  overlap and ambiguity rules before allowing a union's value in later
  arithmetic or cross-field expressions. Predicate acceptance means any branch
  passes; it does not implicitly adopt Pydantic's smart-union selection.
- Make null behavior explicit for cross-field rules and provide declarative
  SQL counterparts to common model validators through the extension API.
- Preserve provenance and readable diagnostics across model-level groups.

Release gate: a truth-table corpus plus database execution verifies grouping,
negation, invalid conversions, branch isolation, and cross-field null behavior.
Existing 2.0 schemas retain their accepted row sets.

## 2.2.0 — Nested and Collection Rules (planned)

Depends on 2.1's branch/group semantics and 2.0's source preparation contract.

- Bind nested rule schemas to JSON paths with explicit key presence rules.
  Keep missing paths, JSON null, and SQL NULL distinct throughout the IR.
- Add discriminator-based tagged unions whose tag and branch fields are
  checked together. Missing or unknown tags have defined failure behavior.
- Add length and element rules for supported SQL arrays and JSON collections.
  Item annotations validate every element; an explicit any-item rule supports
  existential matching. Every-item over an empty collection passes, any-item
  fails, and length constraints can require a nonempty collection.
- Specify item nullability, invalid members, object key/value validation, and
  extraction safety. Publish capabilities per storage representation/version.

Release gate: nested coercion, malformed JSON, missing/null paths, empty
collections, mixed element types, and tag dispatch are covered by executed
backend fixtures. Each advertised operation has a complete support entry.

## 2.3.0 — Schema Features and Integrations (planned)

Depends on the stable typed-expression and adapter extension contracts.

- Add named normalization transforms such as trimming and case conversion
  only when their character/collation semantics are explicit. Order the pipeline
  as source extraction, type matching/coercion, declared transforms, then value
  constraints; strictness still governs the type stage.
- Add registered custom type mappings and explicit SQL expression counterparts
  for selected validators and computed fields. Do not infer SQL from arbitrary
  Python function bodies. Report mismatches in transformation/validation order.
- Export a versioned rule description plus a JSON Schema-compatible subset.
  Mark SQL coercion, column binding, dialect requirements, and model-level
  predicates as extensions or unsupported export features rather than claiming
  standard JSON Schema expresses them all.
- Add examples for Pydantic/FastAPI and SQLAlchemy ORM use, showing conversion
  reports and explicit mappings. Extend schema inspection and diagnostics.

Release gate: exported descriptions agree with compiled behavior, named
transforms have executed semantic fixtures, and custom mappings participate in
capability/conformance checks. Existing schemas keep their previous semantics.

## Requirements Across Every 2.x Phase

- Type/coercion behavior is versioned; a later Pydantic release cannot silently
  change the meaning of an existing SQLRules schema.
- Database execution checks, performance tracking, bounded caches, concurrent
  compilation, diagnostics, docs, and packaging start in 2.0 and continue in
  every phase.
- Compilation enforces all retained rules. Permissive stripping is confined to
  explicit conversion and remains visible in its report.
- Native and converted schemas use the same compiler. Column/source assumptions
  and unsupported features remain inspectable.
- Existing 1.x functionality is tracked through migration fixtures and release
  notes, including deliberate changes to nulls, strictness, and return types.

## Unscheduled Ideas

These need separate semantic and cost proposals before receiving a release:

- Decimal precision constraints and additional string operators.
- Optional persistent IR serialization and code generation.
- Static analysis support and additional dialect plugins.
- Acceleration beyond Python when measured compiler costs justify it.
- Projection of normalized values or whole-table validation reports; the 2.x
  compiler currently produces predicates for caller-executed queries.

## Guiding Principles

Every release should preserve deterministic behavior, expose semantic losses,
keep database I/O with the caller, and honor its documented compatibility
profile. Public API stability includes accepted row sets and error behavior.

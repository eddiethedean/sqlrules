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

Status: **2.0.0 released on 2026-09-26**. The [GitHub Release](https://github.com/eddiethedean/sqlrules/releases/tag/v2.0.0)
and [tagged release workflow](https://github.com/eddiethedean/sqlrules/actions/runs/36253446180)
record the release; all five core and dialect packages are published on PyPI.
The [2.0 design](V2_DESIGN.md) defines the API and semantic contract. Phase
2.1 ends with **2.1.0**, and so on. Internal work packages below are dependency
steps within a release. Dates are assigned after each phase's capability and
conformance scope is fixed.

Core and the four official dialect packages stay in lockstep. Core already
depends on Pydantic v2; the conversion helper ships in the core distribution.
2.0 contains the breaking API and plugin changes; later phases add capabilities
while preserving the 2.0 semantic profile for existing schemas. Additional
coercions that broaden accepted data require an explicit opt-in or profile.

## 2.0.0 — Rule Schemas and Semantic Foundations (released)

The work packages below record the completed scope and acceptance criteria for
2.0.0; they are historical release documentation, not open work.

### Outcome

A user can define or convert a Pydantic-compatible rules model, use it normally
for Python validation and in FastAPI, then compile its SQL-compatible fields
into a safe predicate for one explicitly selected database backend. The
predicate identifies matching rows; `notwhere()` identifies every row that
fails the complete rule set.

### Scope

2.0 includes supported scalar fields and constraints, type-only annotations,
lax and strict behavior, nullable handling, Pydantic metadata normalization,
Pydantic model conversion with a loss report, a total grouped predicate, plugin
API v2, and coordinated releases of core plus all four official dialects.

2.0 does not translate arbitrary Python validators or serializers, expose
general `all()`/`any()` or cross-field rule syntax, add nested JSON schema or
collection item validation, or add named normalization transforms. Those
capabilities remain staged in 2.1–2.3. A full Pydantic model using unsupported
features remains usable in application code; the converter reports or removes
those features before SQL compilation.

### Delivery order

The critical path is **A → B → C → D → E**. Start backend prototypes during A
to test whether proposed coercions are implementable. Finish production dialect
work after the semantic matrix and plugin contract are fixed. E can prepare
migration material while D runs, but release depends on all gates.

### Work package A — Freeze semantics and backend commitments

- Freeze one versioned SQLRules semantic profile: supported logical types,
  lax conversions, strictness precedence, constraint ordering, optional/null
  behavior, Literal/Enum behavior, and the complement used by `notwhere()`.
- For each Pydantic declaration form, classify it as translated, metadata-only,
  or rejected. List supported `Field` options, `Annotated` markers, constrained
  aliases, and `ConfigDict` keys; pin the Pydantic v2 reference version.
- Publish a matrix for PostgreSQL, SQLite, MySQL, and SQL Server. Each entry
  names the server version, source storage type, target type, strictness,
  operator, and one of: supported, requires explicit mapping, or compile error.
  Identify the minimum useful scalar and constraint set required from every
  backend; mark other combinations unsupported instead of leaving them implicit.
- Define the boundary between a row mismatch (predicate false) and a missing
  backend capability (compile error). Record assumptions about SQLite storage,
  emulated bool/date/UUID values, decimal precision, time zones, collation, and
  required database settings.
- Build a reference corpus with ordinary values, SQL NULL, malformed input,
  overflow, fractional values, and boundary values. Compare Python
  `model_validate()` behavior to SQL only where the database exposes equivalent
  source type information; record deliberate differences.

Exit: the semantic profile and matrix contain no unresolved 2.0 decisions.
Every supported entry has expected match/fail examples, and every unsupported
entry has a specific compile-time outcome. Regex shape checks alone do not
qualify as proof of a conversion.

### Work package B — Own declarations and conversion

Depends on A's frozen declaration and validation semantics; prototypes may
start earlier to expose mismatches.

- Implement `RuleSchema` as a Pydantic v2 `BaseModel` subclass. Support ordinary
  construction, `model_validate()`, `model_dump()`, and use in FastAPI. Limit
  declarations at class creation to the A allowlist; do not limit application
  use of a successfully created model.
- Normalize public Pydantic `FieldInfo`, `ConfigDict`, strict/constrained
  aliases, `Annotated` metadata, and supported `annotated_types` markers into
  one immutable schema representation. Keep `sqlrules.Field` for SQL-only
  metadata such as column binding; ordinary constraints need no SQLRules import.
- Resolve forward references before finalization. Reject unsupported field
  types, constraint/type combinations, arbitrary metadata, custom validators,
  serializers, computed fields, and unknown rule-related config with the class
  and field location in the error.
- Preserve defaults and default factories for Python model construction, but
  never turn them into SQL predicates or execute them while extracting rules.
  Preserve title, description, examples, and aliases as runtime/inspection
  metadata; require an explicit policy before aliases affect column binding.
- Implement `from_pydantic()` with `warn`, `drop`, and `raise` policies. Return
  a generated `RuleSchema` class and a deterministic report covering retained
  rules, metadata, dropped features, changed behavior, and uncertainty. Never
  execute source validators, serializers, or default factories to infer SQL.
- Reject empty converted schemas unless explicitly allowed. Reject direct
  compilation of an unrestricted `BaseModel` and point callers to the helper.

Exit: native and converted models normalize to the same schema representation.
Representative Pydantic imports compile, invalid declarations fail during
class creation, generated models still pass Pydantic/FastAPI use, and converter
reports identify each semantic loss without changing the source model.

### Work package C — Compiler IR and result contract

Depends on A; integrates the schema representation from B.

- Define the normalized schema-to-IR boundary. The IR must retain field order,
  source locations, nullability, strictness, coercion profile, and converter
  provenance without retaining table-bound SQL expressions.
- Build typed prepared values and grouped predicates. A prepared value carries
  source/null identity, a safe normalized expression, and a validity predicate;
  constraints operate on the normalized expression. All field rules combine
  under one root predicate.
- Stabilize the public result contract: `CompiledRules.predicate` is the full
  root; `where()` returns a one-item list containing it; `notwhere()` returns a
  one-item list containing its complement; `flatten()` aliases `where()`.
  Diagnostics and `explain()` belong to that compile result.
- Define plugin API v2 with distinct source preparation, capability reporting,
  and constraint translation. Require an explicit backend provider and stable
  capability errors. Do not allow `warn`/`ignore` to omit a retained rule.
- Freeze registry snapshots and isolate per-call state. Do not keep
  diagnostics, mutable payloads, or table-bound expressions in shared schema IR.

Exit: public result behavior is fixed, nullable/grouping semantics are
representable without later API changes, and IR-level truth tables show every
logical result is true or false. Backend execution confirms SQL totality in D.
Concurrent compiles cannot share mutable diagnostics.

### Work package D — Execute safe dialect translations

Depends on the frozen A matrix and C plugin contract. Backend prototypes run
alongside A; production implementation follows the contract.

- Implement every advertised matrix entry in the four official dialect
  packages. Use runtime type evidence where storage permits mixed types; never
  treat SQLite affinity alone as proof of a row's logical type.
- For each supported entry, execute valid, invalid, NULL, malformed, and
  boundary-value fixtures on the stated server version. Confirm unsafe values
  never cause conversion exceptions, even if the optimizer changes evaluation
  order.
- Verify all scalar annotation-only fields and supported constraints, strict
  mismatches, optional branches, Literal/Enum domains, and existing compatible
  dialect markers. Unsupported and mapping-required cases must return stable,
  actionable compile errors.
- For every fixture row, prove exactly one of `where(compiled)` and
  `notwhere(compiled)` selects it. Include rows failing multiple fields,
  required/optional SQL NULLs, failed coercions, and allowed empty schemas.
- Record server versions, database settings, extension requirements, and
  explicit mapping assumptions in the support matrix and compile plan.

Exit: each advertised backend/type/operator combination has execution evidence
on its stated database version. SQL string assertions supplement but cannot
replace those checks.

### Work package E — Migration and coordinated 2.0.0 release

Depends on B, C, and D passing their exits.

- Write migration guidance from direct Pydantic compilation, bare rule
  dictionaries, `emit_type_checks`, and the legacy dialect hint. Preserve the
  spread-style `where()` call and document `notwhere()`.
- Update API, IR, plugin, README, runnable examples, support matrices, and
  release tooling. Remove stale release instructions for plugin API v1 and
  package pins `>=1,<2`; align all five distribution versions at **2.0.0**.
- Run database conformance, converter reports, Pydantic model validation,
  FastAPI request/response checks, concurrent compilation and cache-compatibility
  checks, docs builds, and wheel installation checks from clean environments.
  Record normalization, bind, and full compile performance baselines for later
  comparison.
- Confirm each example in the migration guide runs against its documented
  backend and adapter setup. Publish the frozen type/coercion capability matrix.

Exit: the five packages build and install at **2.0.0**; CI and local release
checks pass; the migration guide maps every removed 1.x input pattern; and all
A–D gates have execution evidence. Tag `v2.0.0` was published on 2026-09-26,
the release workflow passed, and all five distributions are available on
PyPI. Later phases are not prerequisites for the 2.0.0 release.

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
- Database execution checks, performance tracking, cache behavior, concurrent
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

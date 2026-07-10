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

# 0.3.0 --- Plugin System

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

# 0.4.0 --- Dialect Enhancements

## Goals

Provide optimized translations for major databases.

### PostgreSQL

-   regex
-   JSONB
-   ARRAY
-   range operators

### SQLite

-   REGEXP integration
-   JSON helpers

### MySQL / MariaDB

-   JSON operators
-   full-text helpers

### SQL Server

-   JSON support
-   string optimizations

------------------------------------------------------------------------

# 0.5.0 --- Performance

## Goals

Optimize compilation.

### Features

-   persistent metadata cache
-   optimized translator dispatch
-   allocation reductions
-   concurrent-safe caches
-   performance regression CI

Target:

-   Medium model compile \< 2 ms

------------------------------------------------------------------------

# 0.6.0 --- Developer Experience

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

# 0.7.0 --- Ecosystem

## Goals

Integrate with the wider Python ecosystem.

Potential integrations:

-   SQLModel
-   FastAPI
-   Alembic examples
-   Pydantic Settings
-   datamodel-code-generator examples

------------------------------------------------------------------------

# 0.8.0 --- Advanced Constraints

Potential features:

-   decimal precision
-   pattern matching
-   contains
-   starts_with
-   ends_with
-   configurable null policies

Only constraints with deterministic SQL semantics should be accepted.

------------------------------------------------------------------------

# 0.9.0 --- Release Candidate

## Goals

API freeze.

### Activities

-   bug fixing
-   documentation polish
-   performance tuning
-   compatibility verification
-   plugin stabilization

No new major features.

------------------------------------------------------------------------

# 1.0.0 --- Stable Release

## Success Criteria

-   Stable public API
-   Stable plugin API
-   Excellent documentation
-   Comprehensive test suite
-   Cross-dialect compatibility
-   Predictable compiler behavior

### Public API

-   compile()
-   where()
-   flatten()

### Supported Platforms

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

------------------------------------------------------------------------

# Post-1.0 Ideas

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

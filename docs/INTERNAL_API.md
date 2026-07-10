# SQLRules Internal API

## Purpose

This document specifies the internal interfaces used by SQLRules. These
APIs are for implementation and extension within the project and are
**not** part of the public compatibility contract.

The public API should remain small while the internal API may evolve
between minor releases.

------------------------------------------------------------------------

# High-Level Architecture

``` text
compile()
    │
    ▼
Compiler
    │
    ├── ModelInspector
    ├── ColumnResolver
    ├── ConstraintExtractor
    ├── IRBuilder
    ├── TranslatorRegistry
    └── RuleAssembler
```

------------------------------------------------------------------------

# Compiler

The compiler orchestrates the pipeline.

Responsibilities:

-   validate inputs
-   coordinate compilation stages
-   apply compiler options
-   collect diagnostics
-   assemble final rule dictionary

Suggested interface:

``` python
class Compiler:
    def compile(self, model, table):
        ...
```

------------------------------------------------------------------------

# ModelInspector

Reads a Pydantic model without interpreting SQL semantics.

Responsibilities:

-   enumerate fields
-   preserve declaration order
-   expose aliases
-   expose metadata
-   expose annotations

Output:

``` python
list[FieldDescriptor]
```

------------------------------------------------------------------------

# ColumnResolver

Maps model fields to SQLAlchemy columns.

Inputs:

-   SQLAlchemy Table
-   ORM mapped class
-   explicit column map

Output:

``` python
FieldDescriptor -> ColumnElement
```

Raises:

-   MissingColumnError

------------------------------------------------------------------------

# ConstraintExtractor

Converts Pydantic metadata into normalized constraints.

Example:

``` text
Field(age)
    ↓
[
    ge=18,
    le=65,
]
```

↓

``` text
Constraint("ge", 18)
Constraint("le", 65)
```

------------------------------------------------------------------------

# Intermediate Representation (IR)

The IR isolates compiler logic from Pydantic and SQLAlchemy.

Suggested models:

``` python
Constraint
FieldDescriptor
CompilationContext
Diagnostic
```

The IR should contain only semantic information.

------------------------------------------------------------------------

# TranslatorRegistry

Responsible for dispatch.

Suggested methods:

``` python
register(...)
lookup(...)
translate(...)
```

Registry responsibilities:

-   operator lookup
-   dialect overrides
-   plugin registration
-   conflict detection

------------------------------------------------------------------------

# RuleAssembler

Collects expressions into the final output.

Input:

``` python
(field_name, expression)
```

Output:

``` python
{
    "age": [...],
    "name": [...],
}
```

Ordering must be deterministic.

------------------------------------------------------------------------

# CompilationContext

Shared immutable state passed throughout compilation.

Suggested contents:

-   compiler options
-   translator registry
-   dialect
-   diagnostics collector

Avoid global state.

------------------------------------------------------------------------

# Diagnostics

Internal diagnostics should record:

-   warnings
-   skipped constraints
-   plugin decisions

Diagnostics are separate from exceptions.

------------------------------------------------------------------------

# Compiler Pipeline

``` text
Model
 ↓
Inspect
 ↓
Resolve Columns
 ↓
Extract Constraints
 ↓
Build IR
 ↓
Translate
 ↓
Assemble Rules
```

Each stage should be independently unit tested.

------------------------------------------------------------------------

# Internal Stability

The internal API is **not** covered by semantic versioning.

Only the documented public API is guaranteed stable.

Plugins should interact through documented extension points rather than
importing internal modules.

------------------------------------------------------------------------

# Design Principles

-   Small components
-   Single responsibility
-   Immutable data flow
-   Deterministic compilation
-   Clear stage boundaries
-   Testability first
-   Public/private API separation

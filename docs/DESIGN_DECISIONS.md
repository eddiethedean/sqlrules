# SQLRules Design Decisions

## Purpose

This document records the major design decisions behind SQLRules so
future development stays consistent, focused, and easy to reason about.

SQLRules exists to do one thing well:

> Compile constrained Pydantic models into SQLAlchemy WHERE-rule
> dictionaries.

------------------------------------------------------------------------

# Decision 1: SQLRules is a Compiler, Not a Query Builder

## Decision

SQLRules compiles model metadata into SQLAlchemy boolean expressions.

It does not build complete queries.

## Rationale

SQLAlchemy already provides excellent query composition. SQLRules should
produce reusable pieces that fit naturally into SQLAlchemy Core and ORM
workflows.

## Consequences

SQLRules returns expressions such as:

``` python
users.c.age >= 18
```

not full statements such as:

``` python
select(users).where(users.c.age >= 18)
```

------------------------------------------------------------------------

# Decision 2: Return a Dictionary Grouped by Field

## Decision

The primary output format is:

``` python
dict[str, list[ColumnElement[bool]]]
```

Example:

``` python
{
    "age": [
        users.c.age >= 18,
        users.c.age <= 65,
    ],
    "name": [
        func.length(users.c.name) >= 2,
    ],
}
```

## Rationale

A dictionary preserves field-level meaning and lets users compose rules
selectively.

## Consequences

Users can apply all rules:

``` python
stmt = select(users).where(*sqlrules.where(rules))
```

or only some rules:

``` python
stmt = select(users).where(*rules["age"])
```

------------------------------------------------------------------------

# Decision 3: SQLAlchemy Expressions, Not SQL Strings

## Decision

SQLRules returns SQLAlchemy expression objects.

## Rationale

SQL strings are dialect-sensitive, harder to compose, and easier to
misuse. SQLAlchemy expressions are safer, composable, and backend-aware.

## Consequences

SQLRules never renders SQL strings directly.

------------------------------------------------------------------------

# Decision 4: Pydantic v2 First

## Decision

SQLRules targets Pydantic v2 first.

## Rationale

Pydantic v2 has a modern metadata model based heavily on `Annotated` and
constraint metadata. Supporting v1 would add complexity before the
package proves its core value.

## Consequences

Initial compatibility target:

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

Pydantic v1 support may be considered later as a compatibility plugin or
separate adapter.

------------------------------------------------------------------------

# Decision 5: Fail Fast by Default

## Decision

Unsupported constraints raise errors by default.

## Rationale

Silently ignoring constraints could produce overly broad SQL filters and
create correctness or security issues.

## Consequences

Default mode:

``` python
on_unsupported="raise"
```

Optional modes:

-   warn
-   ignore

------------------------------------------------------------------------

# Decision 6: Only Deterministic Constraints Are Supported

## Decision

SQLRules only supports constraints that have deterministic SQL
equivalents.

## Supported Examples

-   gt
-   ge
-   lt
-   le
-   min_length
-   max_length
-   multiple_of
-   Literal
-   Enum

## Unsupported Examples

-   custom validators
-   model validators
-   computed fields
-   arbitrary Python predicates

## Rationale

SQLRules should never pretend that arbitrary Python validation logic can
be safely converted to SQL.

------------------------------------------------------------------------

# Decision 7: Optionality Does Not Generate Rules by Default

## Decision

`Optional[T]` does not automatically produce `IS NULL` or `IS NOT NULL`
expressions.

## Rationale

Optionality describes whether a value may be absent or null during
validation. It does not always imply a SQL filtering rule.

## Consequences

Future configuration may allow explicit nullability policies, but the
default behavior remains no rule.

------------------------------------------------------------------------

# Decision 8: Keep the Intermediate Representation Dialect-Neutral

## Decision

The IR describes semantic intent, not database-specific syntax.

Example:

``` python
Constraint(field="name", operator="min_length", value=2)
```

## Rationale

Dialect-specific behavior belongs in translators, not in the compiler
core.

## Consequences

The same IR can be translated differently by SQLite, PostgreSQL, MySQL,
SQL Server, or Oracle plugins.

------------------------------------------------------------------------

# Decision 9: Plugins Are Explicit (Future)

## Decision

SQLRules 0.1 does **not** ship a plugin API. Customization today is limited
to injecting a `TranslatorRegistry` into `Compiler(registry=...)`.

A future release may add explicit plugin registration (for example
`Compiler(plugins=[...])`) without automatic discovery.

## Rationale

Explicit plugin registration avoids hidden behavior, improves
reproducibility, and keeps the compiler deterministic.

## Consequences

Do not treat plugin examples in design docs as available in 0.1. See
[PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) for the planned design.

------------------------------------------------------------------------

# Decision 10: No Database Connections

## Decision

SQLRules never opens database connections or reflects database metadata.

## Rationale

The package should be safe to use in any environment, including
application startup, tests, CI, and code generation tools.

## Consequences

Users provide SQLAlchemy tables, ORM classes, aliases, or explicit
column maps.

------------------------------------------------------------------------

# Decision 11: Small Public API

## Decision

The public API should remain minimal.

Initial API:

``` python
sqlrules.compile(...)
sqlrules.where(...)
sqlrules.flatten(...)
```

## Rationale

A small API is easier to document, test, stabilize, and maintain.

## Consequences

Advanced behavior should live behind compiler options, internal
components, or plugins rather than expanding the top-level API too
early.

------------------------------------------------------------------------

# Decision 12: Two-Phase Compilation (Future)

## Decision

SQLRules should eventually separate static model compilation from table
binding. **0.1 compiles in a single pass** (inspect → extract → resolve →
translate).

## Planned Phase 1: Static Compilation

- inspect Pydantic model
- extract constraints
- build IR

## Planned Phase 2: Binding

- resolve SQLAlchemy columns
- translate IR to expressions

## Rationale

Static model work can be cached and reused across multiple tables,
aliases, ORM models, or column maps.

## Consequences

This supports better performance and cleaner architecture.

------------------------------------------------------------------------

# Decision 13: Prefer Simple Translators

## Decision

Basic constraints should use simple function-based translators where
possible.

Example:

``` python
"gt": operator.gt
"ge": operator.ge
```

## Rationale

Many translations are direct operator mappings and do not need complex
class hierarchies.

## Consequences

Dedicated translator classes should be reserved for more complex
constraints such as:

-   min_length
-   max_length
-   pattern
-   Literal
-   Enum
-   dialect-specific behavior

------------------------------------------------------------------------

# Decision 14: Stable Errors Matter

## Decision

SQLRules exceptions should be structured and stable.

## Rationale

Clear errors make the package easier to use, test, and integrate into
developer tools.

## Consequences

All public exceptions inherit from:

``` python
SQLRulesError
```

Exceptions should include structured context such as:

-   field
-   constraint
-   value
-   translator
-   suggested fix

------------------------------------------------------------------------

# Decision 15: Documentation Drives Implementation

## Decision

SQLRules planning documents are treated as implementation guidance.

## Rationale

The package is intentionally small, so high-quality design docs can
prevent scope creep and architectural drift.

## Consequences

New features should update relevant docs before implementation.

------------------------------------------------------------------------

# Open Questions

## Should SQLRules Support Pydantic v1?

Likely not in core initially.

Possible future path:

-   `sqlrules-pydantic-v1`
-   adapter layer
-   compatibility mode

------------------------------------------------------------------------

## Should SQLRules Include a CompiledRules Object?

Potential API:

``` python
compiled = sqlrules.compile(UserFilter, users)

compiled.rules
compiled.where()
compiled.field("age")
```

This may improve ergonomics while preserving dictionary output.

------------------------------------------------------------------------

## Should Regex Be Core or Dialect Plugin?

Regex support varies by database.

Likely answer:

-   IR support in core
-   translator support in dialect plugins

------------------------------------------------------------------------

## Should Nullability Rules Be Optional?

Potential future configuration:

``` python
null_policy="ignore"      # default
null_policy="not_null"
null_policy="is_null"
```

This should not be part of the initial MVP unless a strong use case
emerges.

------------------------------------------------------------------------

# Summary

SQLRules should stay small, explicit, deterministic, and composable.

The most important design boundary is this:

> SQLRules converts supported Pydantic constraints into SQLAlchemy WHERE
> expressions. Nothing more.

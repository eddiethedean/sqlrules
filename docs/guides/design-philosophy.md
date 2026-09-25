# Design philosophy

SQLRules compiles a supported subset of Pydantic model declarations into
SQLAlchemy predicates over stored rows.

```text
RuleSchema field declaration  →  type/coercion check + supported constraints
request field value           →  not used as a database filter value
```

## Why it exists

Applications can use one Pydantic model to describe compatible input and row
rules. A `RuleSchema` is still a normal Pydantic model; SQLRules only limits
which declarations it accepts inside the class. An unrestricted Pydantic model
can be converted with `from_pydantic()`, which reports the semantics it drops.

## Principles

- **Compile predicates, not queries.** SQLRules returns a `CompiledRules`
  result; applications compose its root predicate into SQLAlchemy statements.
- **Type annotations matter.** A scalar annotation adds a row type rule. Lax
  coercion follows the SQLRules profile, and strict mode checks the observable
  database type.
- **Fail rather than guess.** Known row mismatches are false. Missing backend
  capabilities and unsupported retained rules raise errors.
- **Make complements total.** `where()` selects matching rows and `notwhere()`
  selects rows that fail the complete rule set, including NULLs and failed
  conversions.
- **No database I/O.** Compilation builds SQLAlchemy expressions and does not
  connect to a database or execute statements.
- **Select providers explicitly.** Dialect packages implement source
  preparation and constraints. `dialect=` does not load a backend.

## What SQLRules is not

It is not an ORM, request-value filter, general query builder, SQL string
generator, migration tool, or database client. Applications remain responsible
for composing queries and executing them through SQLAlchemy.

## When not to use it

- You need request values to become SQL equality predicates.
- You have a small number of static filters and do not need shared model rules.
- You need a dialect feature that is not in the support matrix.
- You expect the compiler to discover a provider from an engine or dialect.

See [VISION](../VISION.md), [DESIGN_DECISIONS](../DESIGN_DECISIONS.md), and
[ARCHITECTURE](../ARCHITECTURE.md).

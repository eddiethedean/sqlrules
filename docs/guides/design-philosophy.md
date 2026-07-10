# Design philosophy

SQLRules does **one** job: compile a safe subset of Pydantic constraints into
SQLAlchemy WHERE expressions.

## Why it exists

Applications often encode filter intent twice—once in Pydantic models and
again as hand-written SQLAlchemy clauses. SQLRules keeps a single source of
truth: the model’s constraints become deterministic column expressions.

## Principles

- **Do one thing well.** Not an ORM, validator, query builder, SQL string
  generator, migration tool, or database client.
- **Deterministic output.** Same model + table → same rule dictionary order
  and expressions.
- **Refuse to guess.** If a Pydantic feature cannot be translated safely, the
  compiler raises (or warns/ignores for unknown *operators* when configured).
- **Zero database dependency.** Compilation never connects to a database.
- **Plugins for dialects.** Portable core; dialect-specific operators live in
  versioned plugins.

## What SQLRules is not

See [NON_GOALS](../NON_GOALS.md). Applications remain responsible for composing
queries, choosing dialects, and executing SQL through SQLAlchemy.

## When *not* to use it

If you have a couple of static filters and will never share constraint
metadata with a Pydantic model, write the SQLAlchemy expressions directly.
SQLRules pays off when the model is the shared source of truth across many
fields or dialects.

## Deeper reading

- [VISION](../VISION.md) · [PHILOSOPHY](../PHILOSOPHY.md)
- [DESIGN_DECISIONS](../DESIGN_DECISIONS.md)
- [ARCHITECTURE](../ARCHITECTURE.md)

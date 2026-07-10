# Design philosophy

SQLRules does **one** job: compile a safe subset of Pydantic **Field
constraint metadata** into SQLAlchemy WHERE expressions.

```text
Field(ge=18)           →  column >= 18
UserFilter(age=25)     →  column == 25   # NOT what SQLRules does
```

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
- **No database I/O.** Compilation never connects to a database (it still
  depends on the SQLAlchemy library for expression objects).
- **Plugins for dialects.** Portable core; dialect-specific operators live in
  versioned plugins. `dialect=` is a hint only — it does not load plugins.

## What SQLRules is not

See [NON_GOALS](../NON_GOALS.md). Applications remain responsible for composing
queries, choosing dialects, and executing SQL through SQLAlchemy.

## When *not* to use it

Skip SQLRules when:

- You need **request/instance values** as WHERE predicates.
- You have a couple of static filters and will never share constraint
  metadata with a Pydantic model — write SQLAlchemy expressions directly.
- You need **portable regex** with core alone (`pattern` needs a plugin).
- You expect `dialect=` to load plugins automatically.
- You want a general-purpose query builder or SQL string generator.

SQLRules pays off when the model is the shared source of truth across many
fields or dialects.

## Deeper reading

- [VISION](../VISION.md) · [PHILOSOPHY](../PHILOSOPHY.md) · [NON_GOALS](../NON_GOALS.md)
- [DESIGN_DECISIONS](../DESIGN_DECISIONS.md) (internals)
- [ARCHITECTURE](../ARCHITECTURE.md)

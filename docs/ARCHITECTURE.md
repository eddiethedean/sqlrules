# Architecture

```text
Pydantic Model
    ↓
Metadata Reader
    ↓
Constraint IR
    ↓
SQLAlchemy Compiler
    ↓
Rule Dictionary
```

SQLRules is a pure compiler pipeline:

1. **Inspect** the Pydantic model and preserve field declaration order.
2. **Resolve** each field to a SQLAlchemy column.
3. **Extract** supported constraints into a dialect-neutral IR.
4. **Translate** each IR constraint into one SQLAlchemy expression.
5. **Assemble** expressions into `dict[str, list[ColumnElement[bool]]]`.

The compiler never connects to a database, executes SQL, or renders SQL
strings. See [COMPILER.md](COMPILER.md) and [INTERNAL_API.md](INTERNAL_API.md)
for stage-level detail.

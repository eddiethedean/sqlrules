# Architecture

```text
Pydantic Model
    ↓
Metadata Reader  (cached ModelIR)
    ↓
Constraint IR
    ↓
Column Binding
    ↓
SQLAlchemy Compiler
    ↓
Rule Dictionary (+ diagnostics)
```

SQLRules is a pure compiler pipeline with two phases:

**Phase 1 — static model IR**

1. **Inspect** the Pydantic model and preserve field declaration order.
2. **Extract** supported constraints into a dialect-neutral IR.
3. **Cache** immutable `ModelIR` keyed by model class (optional).

**Phase 2 — bind and translate**

4. **Resolve** each constrained field to a SQLAlchemy column.
5. **Translate** each IR constraint into one SQLAlchemy expression.
6. **Assemble** expressions into `dict[str, list[ColumnElement[bool]]]`.

The compiler never connects to a database, executes SQL, or renders SQL
strings. See [COMPILER.md](COMPILER.md) and [INTERNAL_API.md](INTERNAL_API.md)
for stage-level detail.

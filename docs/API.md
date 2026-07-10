# Public API

SQLRules exposes a deliberately small public surface.

## `compile`

```python
sqlrules.compile(
    model,
    table,
    *,
    column_map=None,
    on_unsupported="raise",
) -> dict[str, list[ColumnElement[bool]]]
```

Compile a constrained Pydantic model into a field-keyed rule dictionary.

| Parameter | Description |
|---|---|
| `model` | Pydantic `BaseModel` subclass |
| `table` | SQLAlchemy `Table`, alias, ORM class, or object with `.c` |
| `column_map` | Optional explicit `field_name` or alias → column mapping |
| `on_unsupported` | `"raise"` (default), `"warn"`, or `"ignore"` for unknown **operators** only |

Rule dictionary keys are always the Python field names. String field aliases
(`alias`, `validation_alias`, `serialization_alias`) are used only for column
binding. Unconstrained fields are omitted and do not require a column.

Unsupported types always raise, regardless of `on_unsupported`.

## `where` / `flatten`

```python
sqlrules.where(rules) -> list[ColumnElement[bool]]
sqlrules.flatten(rules) -> list[ColumnElement[bool]]
```

Flatten a rule dictionary into a single list of expressions suitable for
`Query.where(*expressions)` or `select(...).where(*expressions)`.

`where` and `flatten` are identical aliases.

## `Compiler`

```python
compiler = sqlrules.Compiler(on_unsupported="raise", registry=None)
rules = compiler.compile(model, table, column_map=None)
```

Reusable compiler instance with a fixed unsupported-constraint policy and
optional custom translator registry.

## Other exports

Also exported for advanced use and typing:

- `__version__`
- `SQLRulesWarning`
- `CompilationContext`, `Constraint`, `FieldDescriptor` (IR helpers)

## Exceptions

All public exceptions inherit from `SQLRulesError`:

- `InvalidModelError`
- `MissingColumnError`
- `UnsupportedConstraintError`
- `TranslatorError`
- `InvalidTranslatorError` (reserved; not raised in 0.1)
- `RegistryError`
- `ConfigurationError`
- `InternalCompilerError` (reserved; not raised in 0.1)

See [ERRORS.md](ERRORS.md) for details.

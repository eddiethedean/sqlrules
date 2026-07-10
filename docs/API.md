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
| `column_map` | Optional explicit `field_name → column` mapping |
| `on_unsupported` | `"raise"` (default), `"warn"`, or `"ignore"` |

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
compiler = sqlrules.Compiler(on_unsupported="raise")
rules = compiler.compile(model, table, column_map=None)
```

Reusable compiler instance with a fixed unsupported-constraint policy and
translator registry.

## Exceptions

All public exceptions inherit from `SQLRulesError`:

- `InvalidModelError`
- `MissingColumnError`
- `UnsupportedConstraintError`
- `TranslatorError`
- `InvalidTranslatorError`
- `RegistryError`
- `ConfigurationError`
- `InternalCompilerError`

See [ERRORS.md](ERRORS.md) for details.

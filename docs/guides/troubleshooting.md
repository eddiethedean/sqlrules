# Troubleshooting

## `UnsupportedConstraintError`

An operator or type has no translator.

- Check [CONSTRAINTS](../CONSTRAINTS.md) and [TYPE_SUPPORT](../TYPE_SUPPORT.md).
- For `pattern` / dialect markers, install a plugin and pass
  `Compiler(plugins=[...])` (or register a translator).
- For unknown **operators** only, try `on_unsupported="warn"` or `"ignore"`.
  Unsupported **types** always raise.
- `emit_type_checks=True` without a `type_check` translator raises the same
  way as bare `pattern` — install a dialect plugin or register a translator.

## `pattern` still unsupported with `sqlrules-mssql`

Expected: the MSSQL plugin does **not** register `pattern`. Use PostgreSQL /
SQLite / MySQL plugins, a custom translator, or drop the constraint.

## `pattern` compiles but SQLite queries fail / never match

`sqlrules-sqlite` emits `REGEXP`. Call
`sqlrules_sqlite.register_regexp(connection)` on each connection (or via a
SQLAlchemy `connect` event). Until then, SQLite has no REGEXP implementation.
See [DIALECT_SUPPORT](../DIALECT_SUPPORT.md) and [SECURITY](../SECURITY.md)
(Python `re` runs in-process).

## `MissingColumnError`

A constrained field could not bind to a column.

```python
rules = sqlrules.compile(
    Model,
    table,
    column_map={"field_or_alias": table.c.actual_column},
)
```

- Confirm the table/ORM attribute is a real column (not `Table.name`, etc.).
- String aliases on `Field` are tried before the Python field name.
- Full walkthrough: [ORM / column_map](orm-column-map.md).

## Plugin registration conflicts

Two plugins (or a plugin and a builtin) claim the same operator.

- Set `on_conflict="replace"` or `"ignore"` on `Compiler` / `register_constraint`.
- Default is `"raise"`. See [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md).

## Plugin API version mismatch

`api_version` must equal `sqlrules.PLUGIN_API_VERSION` (`"1"`). Upgrade the
plugin or core so they match.

## Rules look wrong / empty

- Unconstrained fields are omitted.
- Confirm you are inspecting the returned dict, not re-validating the model
  or expecting instance values in the WHERE clause.
- For two-phase use, call `bind` after `compile_model`.
- `dialect=` alone never loads plugins — pass `plugins=[...]`.

## `pip` installs an old version / dialect package 404

SQLRules **1.0.0** (and dialect packages) must be published on PyPI for
`pip install sqlrules-postgresql` to work. Until then, clone the repository
and run `make install`, or install wheels from `dist/` and `dist-plugins/`.
See the [README install section](https://github.com/eddiethedean/sqlrules#install).

## Still stuck?

- [FAQ](faq.md) · [ERRORS](../ERRORS.md) · [SECURITY](../SECURITY.md)
- Open an issue: https://github.com/eddiethedean/sqlrules/issues

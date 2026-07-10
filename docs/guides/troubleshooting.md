# Troubleshooting

## `UnsupportedConstraintError`

An operator or type has no translator.

- Check [CONSTRAINTS](../CONSTRAINTS.md) and [TYPE_SUPPORT](../TYPE_SUPPORT.md).
- For `pattern` / dialect markers, install a plugin or register a translator.
- For unknown **operators** only, try `on_unsupported="warn"` or `"ignore"`.
  Unsupported **types** always raise.

## `MissingColumnError`

A constrained field could not bind to a column.

- Pass an explicit `column_map={field_or_alias: column}`.
- Confirm the table/ORM attribute is a real column (not `Table.name`, etc.).
- String aliases on `Field` are tried before the Python field name.

## Plugin registration conflicts

Two plugins (or a plugin and a builtin) claim the same operator.

- Set `on_conflict="replace"` or `"ignore"` on `Compiler` / `register_constraint`.
- Default is `"raise"`. See [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md).

## Plugin API version mismatch

`api_version` must equal `sqlrules.PLUGIN_API_VERSION` (`"1"`). Upgrade the
plugin or core so they match.

## Rules look wrong / empty

- Unconstrained fields are omitted.
- Confirm you are inspecting the returned dict, not re-validating the model.
- For two-phase use, call `bind` after `compile_model`.

## Still stuck?

- [FAQ](faq.md) · [ERRORS](../ERRORS.md) · [SECURITY](../SECURITY.md)
- Open an issue: https://github.com/eddiethedean/sqlrules/issues

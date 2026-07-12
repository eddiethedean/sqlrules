# Upgrade from 0.x to 1.0

## Install

```bash
pip install "sqlrules>=1,<2"
```

Dialect plugins are **separate packages** on the same major line:

```bash
pip install "sqlrules-postgresql>=1,<2"   # or sqlite / mysql / mssql
# or: pip install "sqlrules[postgresql]" / "sqlrules[dialects]"
```

## What stayed the same

- `compile`, `where` / `flatten`, and `Compiler` remain the Application API
- Core still compiles comparisons, lengths, `Literal`, and `Enum`
- `pattern` still needs a dialect plugin or custom translator
- `dialect=` is still a hint only — pass `plugins=[...]` explicitly

## What to expect in 1.0

- Application + Plugin APIs are **frozen** for the 1.x line
- Official plugins: PostgreSQL, SQLite, MySQL, MSSQL
- Opt-in `emit_type_checks` / `TypeSpec` (plugin-translated, same footgun as
  `pattern` without a translator)
- Pins: plugins require `sqlrules>=1,<2`; core extras pull `sqlrules-*>=1,<2`

## Breaking / behavioral notes from 0.x

- Unsupported types still always raise (not softened by `on_unsupported`)
- Prefer `register_constraint(..., on_conflict=...)` over legacy `replace=`
- Whole-model type matrix: unconstrained fields with unsupported annotations
  raise; unconstrained supported types are omitted from the rules dict

See [CHANGELOG](../project/changelog.md) for the full 1.0.0 notes.

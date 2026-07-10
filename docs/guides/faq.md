# FAQ

## What does SQLRules actually return?

A dictionary mapping **Python field names** to lists of SQLAlchemy boolean
`ColumnElement`s. Use `sqlrules.where(rules)` (alias `flatten`) to pass them
to `.where(...)`.

## Does it validate request data or apply instance values?

No. Pydantic still validates inputs. SQLRules only reads **constraint
metadata** (`Field(ge=18)`, `min_length`, markers, …) and compiles
expressions. Runtime values such as `UserFilter(age=25)` are **not** turned
into `column == 25`.

## Why doesn’t `pattern` work out of the box?

`pattern` is extracted into IR as `PatternSpec`, but there is no portable
regex operator across databases. Install a dialect plugin or register a
custom translator. See [CONSTRAINTS](../CONSTRAINTS.md) and
[PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md).

SQL Server (`sqlrules-mssql`) does **not** register `pattern`.

## How do I use JSON / array / full-text operators?

Use markers from `sqlrules.markers` (for example `JsonContains`) in
`Annotated[...]`, then compile with a dialect plugin that registers those
operators. See [Use dialect markers](markers.md).

## What is `dialect=` on `Compiler`?

A **hint** for translators—not automatic dialect detection and **not** plugin
loading. Pass `plugins=[...]` explicitly. See [API](../API.md).

## `compile` vs `Compiler`?

Module-level `sqlrules.compile` is the one-shot Application API (no plugins).
Use `Compiler(plugins=[...])` when you need plugins, a custom registry, or
two-phase `compile_model` / `bind`.

Do not call `compile` / `bind` concurrently on the **same** `Compiler`
instance.

## How do I bind ORM models or renamed columns?

Pass a Declarative class as `table`, or use `column_map={...}`. See
[ORM / column_map](orm-column-map.md).

## Why did an unconstrained field disappear from the rules dict?

Fields with no supported constraints are omitted from the rules dict. Their
**types** must still be in the support matrix (whole-model rule).

Pass `emit_type_checks=True` to emit `type_check` IR for supported scalar
annotations (requires a dialect plugin or custom translator to bind — same
footgun as `pattern`).

## When should I clear the model IR cache?

Call `sqlrules.clear_model_cache()` when creating many ephemeral models
(`pydantic.create_model`) so the process-wide Phase-1 cache does not grow
without bound. Use `cache=False` on `compile` / `Compiler` to skip caching
for a one-off compile.

## Where is the stable API boundary?

[API](../API.md) documents Application, Plugin, and Internal tiers. Semver
applies to Application and Plugin surfaces. See also
[Support & compatibility](../project/support.md).

## More help

[Troubleshooting](troubleshooting.md) · [Errors](../ERRORS.md) ·
[Start here](start-here.md)

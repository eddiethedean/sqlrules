# FAQ

## What does SQLRules actually return?

A dictionary mapping **Python field names** to lists of SQLAlchemy boolean
`ColumnElement`s. Use `sqlrules.where(rules)` (alias `flatten`) to pass them
to `.where(...)`.

## Does it validate request data?

No. Pydantic still validates inputs. SQLRules only reads constraint metadata
and compiles expressions. Runtime values are not applied by the compiler.

## Why doesn’t `pattern` work out of the box?

`pattern` is extracted into IR as `PatternSpec`, but there is no portable
regex operator across databases. Install a dialect plugin or register a
custom translator. See [CONSTRAINTS](../CONSTRAINTS.md) and
[PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md).

## How do I use JSON / array / full-text operators?

Use markers from `sqlrules.markers` (for example `JsonContains`) in
`Annotated[...]`, then compile with a dialect plugin that registers those
operators.

## What is `dialect=` on `Compiler`?

A **hint** for translators—not automatic dialect detection. Plugins decide
how to use it. See [API](../API.md).

## `compile` vs `Compiler`?

Module-level `sqlrules.compile` is the one-shot Application API (no plugins).
Use `Compiler(plugins=[...])` when you need plugins, a custom registry, or
two-phase `compile_model` / `bind`.

## Why did an unconstrained field disappear from the rules dict?

Fields with no supported constraints are omitted from the rules dict. Their
**types** must still be in the support matrix (whole-model rule).

Pass `emit_type_checks=True` to emit `type_check` IR for supported scalar
annotations (requires a dialect plugin or custom translator to bind).

## How do I clear the model IR cache?

Call `sqlrules.clear_model_cache()` when creating many ephemeral models so the
process-wide Phase-1 cache does not grow without bound.

## Where is the stable API boundary?

[API](../API.md) documents Application, Plugin, and Internal tiers. Semver
applies to Application and Plugin surfaces.

## More help

[Troubleshooting](troubleshooting.md) · [Errors](../ERRORS.md) ·
[Start here](start-here.md)

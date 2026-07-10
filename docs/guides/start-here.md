# Start here

Pick the path that matches what you need. Each link is a single next step—not
the full documentation map.

## I want to compile constraints from a Pydantic model

[Getting started](getting-started.md) — install `sqlrules`, compile one model,
and attach the rules to a SQLAlchemy `select()`.

Remember: SQLRules compiles **Field metadata** (`ge=18`), not instance values
(`UserFilter(age=25)`).

## I need dialect-specific operators (regex, JSON, arrays)

[Use dialect markers](markers.md) · [Plugin system](../PLUGIN_SYSTEM.md) —
install a dialect package (`sqlrules-postgresql`, `sqlrules-sqlite`,
`sqlrules-mysql`, or `sqlrules-mssql`) and register it on `Compiler`.

## I need ORM / renamed column binding

[ORM / column_map](orm-column-map.md)

## I am evaluating SQLRules for my stack

[Design philosophy](design-philosophy.md) · [Support & compatibility](../project/support.md) ·
[Specification](../SPEC.md) · [Security](../SECURITY.md)

## I am writing a custom translator or plugin

[Plugin system](../PLUGIN_SYSTEM.md) · [Translators](../TRANSLATORS.md) ·
[API tiers](../API.md)

## I want the generated API surface

[Reference hub](../reference/index.md) · [Application autodoc](../reference/application.md) ·
[Glossary](../reference/glossary.md)

## I am stuck

[FAQ](faq.md) · [Troubleshooting](troubleshooting.md) · [Errors](../ERRORS.md)

## I want to contribute

[Contributing](../project/contributing.md)

## Full documentation map

Return to the [documentation home](../index.md#documentation-map) for the
complete table of contents.

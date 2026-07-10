# Reference

Contract and generated API for SQLRules {{ release }}.

When narrative docs and autodoc disagree, **trust the installed package
signatures and autodoc**, then file an issue against the narrative page.
Narrative docs explain *why* and *when*; autodoc is the
parameter / return / exception contract.

## Start with a guide

| Goal | Read first | Then |
|---|---|---|
| Compile constraints | [Getting started](../guides/getting-started.md) | [SPEC](../SPEC.md) · [CONSTRAINTS](../CONSTRAINTS.md) |
| ORM / aliases | [ORM / column_map](../guides/orm-column-map.md) | [Troubleshooting](../guides/troubleshooting.md) |
| Markers / dialects | [Markers](../guides/markers.md) | [DIALECT_SUPPORT](../DIALECT_SUPPORT.md) |
| Public surface | [API](../API.md) | [Application autodoc](application.md) |
| Plugins | [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md) | [Plugin autodoc](plugin-api.md) · [IR_CONTRACT](../IR_CONTRACT.md) |
| Terms | [Glossary](glossary.md) | — |

## Application API (narrative)

- [SPEC](../SPEC.md) — return shape, binding, unsupported policy
- [API](../API.md) — Application / Plugin / Internal tiers
- [IR_CONTRACT](../IR_CONTRACT.md) — frozen Plugin API v1 IR schema
- [CONSTRAINTS](../CONSTRAINTS.md) — operator → expression map
- [TYPE_SUPPORT](../TYPE_SUPPORT.md) · [ERRORS](../ERRORS.md) · [SECURITY](../SECURITY.md)

## Plugin & dialect reference

- [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md)
- [TRANSLATORS](../TRANSLATORS.md)
- [DIALECT_SUPPORT](../DIALECT_SUPPORT.md)

## Generated API

- [Application autodoc](application.md) — `compile`, `where`, `Compiler`, markers
- [Plugin / IR autodoc](plugin-api.md) — registry, IR types, plugin protocol

Import markers from `sqlrules` (re-exported) or `sqlrules.markers`.

## Architecture (explanation)

- [Internals hub](../internals/index.md)
- [ARCHITECTURE](../ARCHITECTURE.md) · [COMPILER](../COMPILER.md)
- [INTERNAL_API](../INTERNAL_API.md)

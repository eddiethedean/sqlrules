# Reference

Contract and generated API for SQLRules {{ release }}.

When narrative docs and autodoc disagree, **prefer the narrative guide** and
file an issue if the signatures are wrong.

## Start with a guide

| Goal | Read first | Then |
|---|---|---|
| Compile filters | [Getting started](../guides/getting-started.md) | [SPEC](../SPEC.md) · [CONSTRAINTS](../CONSTRAINTS.md) |
| Public surface | [API](../API.md) | [Application autodoc](application.md) |
| Plugins / dialects | [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md) | [Plugin autodoc](plugin-api.md) · [IR_CONTRACT](../IR_CONTRACT.md) |
| Terms | [Glossary](glossary.md) | — |

## Application API (narrative)

- [SPEC](../SPEC.md) — return shape, binding, unsupported policy
- [API](../API.md) — Application / Plugin / Internal tiers
- [IR_CONTRACT](../IR_CONTRACT.md) — frozen Plugin API v1 IR schema
- [CONSTRAINTS](../CONSTRAINTS.md) — operator → expression map
- [TYPE_SUPPORT](../TYPE_SUPPORT.md) · [ERRORS](../ERRORS.md)

## Plugin & dialect reference

- [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md)
- [TRANSLATORS](../TRANSLATORS.md)
- [DIALECT_SUPPORT](../DIALECT_SUPPORT.md)

## Generated API

- [Application autodoc](application.md) — `compile`, `where`, `Compiler`, markers
- [Plugin / IR autodoc](plugin-api.md) — registry, IR types, plugin protocol

Import markers from `sqlrules` (re-exported) or `sqlrules.markers`.

## Architecture (explanation)

- [ARCHITECTURE](../ARCHITECTURE.md) · [COMPILER](../COMPILER.md)
- [INTERNAL_API](../INTERNAL_API.md)

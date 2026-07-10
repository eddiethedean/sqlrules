# SQLRules Documentation

SQLRules compiles a safe subset of Pydantic constraints into SQLAlchemy
WHERE expressions.

## Start here

- [README](../README.md) — quick start and install
- [SPEC](SPEC.md) — 0.1 contract
- [API](API.md) — public surface
- [CONSTRAINTS](CONSTRAINTS.md) — constraint → expression map

## Architecture

- [ARCHITECTURE](ARCHITECTURE.md) — high-level pipeline
- [COMPILER](COMPILER.md) — compilation stages
- [TRANSLATORS](TRANSLATORS.md) — IR → SQLAlchemy
- [INTERNAL_API](INTERNAL_API.md) — internal components
- [ERRORS](ERRORS.md) — exception hierarchy and policies

## Compatibility

- [TYPE_SUPPORT](TYPE_SUPPORT.md) — supported Python / Pydantic types
- [DIALECT_SUPPORT](DIALECT_SUPPORT.md) — portable vs dialect-specific behavior
- [TESTING](TESTING.md) — test strategy

## Design

- [VISION](VISION.md)
- [PHILOSOPHY](PHILOSOPHY.md)
- [NON_GOALS](NON_GOALS.md)
- [DESIGN_DECISIONS](DESIGN_DECISIONS.md)

## Future

- [ROADMAP](ROADMAP.md)
- [MILESTONES](MILESTONES.md)
- [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md)
- [PERFORMANCE](PERFORMANCE.md)

## Contributing

- [CONTRIBUTING](../CONTRIBUTING.md)

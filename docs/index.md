# SQLRules Documentation

SQLRules compiles a safe subset of Pydantic constraints into SQLAlchemy
WHERE expressions.

## Start here

- [README](../README.md) — quick start and install
- [SPEC](SPEC.md) — contract
- [API](API.md) — public surface
- [CONSTRAINTS](CONSTRAINTS.md) — constraint → expression map
- [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md) — versioned plugins and dialect packages

## Architecture

- [ARCHITECTURE](ARCHITECTURE.md) — high-level pipeline
- [COMPILER](COMPILER.md) — compilation stages
- [TRANSLATORS](TRANSLATORS.md) — IR → SQLAlchemy
- [INTERNAL_API](INTERNAL_API.md) — internal components
- [ERRORS](ERRORS.md) — exception hierarchy and policies

## Compatibility

- [TYPE_SUPPORT](TYPE_SUPPORT.md) — supported Python / Pydantic types
- [DIALECT_SUPPORT](DIALECT_SUPPORT.md) — portable vs dialect-specific behavior
- [SECURITY](SECURITY.md) — trust model and ReDoS notes
- [TESTING](TESTING.md) — test strategy

## Design

- [VISION](VISION.md)
- [PHILOSOPHY](PHILOSOPHY.md)
- [NON_GOALS](NON_GOALS.md)
- [DESIGN_DECISIONS](DESIGN_DECISIONS.md)

## Planning

- [ROADMAP](ROADMAP.md)
- [MILESTONES](MILESTONES.md)
- [PERFORMANCE](PERFORMANCE.md)

## Contributing

- [CONTRIBUTING](../CONTRIBUTING.md)

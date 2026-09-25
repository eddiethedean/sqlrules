# Roadmap

The 2.x series introduces SQLRules-owned rule schemas and an explicit Pydantic
conversion bridge. Phase 2.0 is in implementation; its release gates remain
open until database conformance and package checks pass.
API sketches and semantic decisions live in [the 2.0 design](docs/V2_DESIGN.md),
with implementation steps and release gates in [Milestones](docs/MILESTONES.md).

Each phase ends in a stable release: **2.0 → 2.0.0**, **2.1 → 2.1.0**, and so on.
Implementation steps inside a phase are work packages, not separate releases.
Core and all four official dialect packages remain versioned together.

| Phase | Release | Outcome |
|---|---|---|
| 2.0 | 2.0.0 | Pydantic-compatible RuleSchema models, safe coercion and strict checks, explicit conversion, stable compiler foundation |
| 2.1 | 2.1.0 | Public boolean composition, scalar unions, and cross-field rules |
| 2.2 | 2.2.0 | Nested JSON schemas, tagged unions, and collection rules |
| 2.3 | 2.3.0 | Named transforms, custom type mappings, schema export, and integration tools |

## 2.0.0 — Rule schemas and semantic foundations (implementation in progress)

- Own `RuleSchema`, `Field`, and `RuleConfig` on Pydantic v2. Models retain
  normal construction, validation, serialization, and FastAPI use. Restrict
  declarations to SQL-compatible types and constraints; reject incompatible
  declarations when the class is created. Model use remains unrestricted.
- Accept Pydantic's own `Field`, `ConfigDict`, strict/constrained type aliases,
  and compatible `Annotated` metadata such as `StringConstraints` and
  `annotated_types` markers. Keep SQLRules helpers for SQL-only settings such
  as column mapping and empty-schema policy.
- Every scalar annotation contributes a predicate. Lax mode is the default;
  schema and field settings can require strict matching of the observed logical
  type. Document each backend's storage mappings and coercion support.
- Prepare a safe typed expression before applying constraints. Invalid values
  are non-matches; nullable branches wrap the entire field rule. Conversion
  safety cannot depend on SQL evaluating AND clauses in a particular order.
- Introduce grouped IR and `CompiledRules` with a complete predicate, immutable
  diagnostics, and an inspectable compilation plan. These foundations ship in
  2.0 even though richer public composition arrives in 2.1. Keep `where()`'s
  list return and add `notwhere()` to select every failure, including rows with
  SQL NULL or invalid conversions.
- Add `from_pydantic()` in `sqlrules.integrations.pydantic`. Conversion strips
  incompatible declarations according to an explicit policy and reports
  semantic changes. The original remains a normal Pydantic model, and the
  converted result is also a usable Pydantic model. Compilation always enforces
  every retained rule.
- Introduce plugin API v2, explicit backend capabilities, immutable normalized
  schema metadata, and independent compilation state. Provide migration from direct Pydantic
  input, bare rule dictionaries, and opt-in type checks.

Release gate: freeze and implement a useful capability matrix for all four
backends, prove supported behavior with database execution tests, and show that
`where(compiled)` matches and `notwhere(compiled)` failures partition each tested
row set. Complete migration, docs, and package checks. Publish the first stable
2.0 as **2.0.0**.

## 2.1.0 — Rule composition (planned)

- Expose all/any/not groups and explicit cross-field comparisons on the typed
  expression foundation from 2.0.
- Support scalar unions as grouped alternatives with documented coercion and
  branch behavior. Keep typed expressions scoped to their branch.
- Provide declarative SQL counterparts to common model validators.

Release gate: composed predicates preserve grouping, conversion safety, and
null behavior. Public `not` groups use the root complement semantics established
in 2.0. Existing 2.0 schemas keep their semantics under the 2.0 profile.

## 2.2.0 — Structured values (planned)

- Bind nested rule schemas to JSON paths; distinguish missing paths, JSON null,
  and SQL NULL, with explicit presence rules.
- Add discriminator-based tagged unions and supported collection length rules.
- Interpret item annotations as checks on every item. Add an explicit any-item
  operator and define empty-collection and invalid-item behavior.

Release gate: executed backend fixtures establish the advertised support matrix
for nested values, collections, and tagged branches. Unsupported storage or
operations produce actionable compilation errors.

## 2.3.0 — Schema features and integrations (planned)

- Add named normalization transforms with a fixed evaluation order, applying
  them to safe expressions before value constraints.
- Add registered custom type mappings and explicit SQL expression counterparts
  for selected Pydantic features. Conversion reports identify behavior changes.
- Export rule metadata and a JSON Schema-compatible subset, marking SQL-specific
  semantics explicitly. Add API and ORM integration examples.

Release gate: transformation order, exported metadata, and converter reports
agree with executed predicates. New conversions are explicitly enabled when
needed to preserve existing result sets.

## Quality and compatibility across 2.x

Database execution conformance, compiler benchmarks, diagnostics, concurrent
compilation behavior, documentation, and package checks begin in 2.0 and continue through
every phase. Later releases extend the supported vocabulary without silently
changing the acceptance rules of existing schemas. Pydantic compatibility is a
versioned, documented subset with explicit SQL storage differences.

## Delivered through 1.x

- **0.1:** numeric/string constraints, Literal/Enum, compiler, tests, docs, CI.
- **0.2:** two-phase compilation, IR caching, diagnostics, temporal/UUID support.
- **0.3:** versioned translator plugins and registry conflict policies.
- **0.4:** JSON, array, range, regex, and full-text dialect extensions.
- **1.0 / 1.0.1:** stable application/plugin APIs, opt-in type checks,
  coordinated packaging, contract documentation, and stronger behavioral tests.

See [Changelog](https://github.com/eddiethedean/sqlrules/blob/main/CHANGELOG.md)
for delivered features and [Milestones](docs/MILESTONES.md)
for the historical phase descriptions and unscheduled ideas.

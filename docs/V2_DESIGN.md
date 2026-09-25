# SQLRules 2.0 Design

Status: SQLRules 2.0 implementation contract. The core and four official
packages target the 2.0.0 line; the milestone gates track remaining release
conformance evidence.
See [Milestones](MILESTONES.md) for implementation order and release scope.

## Product contract

SQLRules owns a restricted `RuleSchema` model, built on Pydantic v2, and
compiles its supported fields into a predicate over database rows. Native rule
models can be constructed with `__init__`, validated with `model_validate`,
and inspected or serialized with the usual Pydantic model APIs. SQLRules checks
model declarations against its own supported subset. Every supported scalar
annotation contributes a type rule. Lax mode accepts the documented
conversions and evaluates constraints on the converted expression. Strict mode
requires the declared logical type. Optional fields accept SQL NULL. Full
Pydantic models enter through an explicit converter that reports incompatible
behavior it removes.

The compiler produces SQLAlchemy expressions without database I/O. Its WHERE
predicate selects matching rows; it neither rewrites stored values nor changes
the values projected by a SELECT. Checking that an entire table passes requires
a caller-executed query for rows failing the predicate.

## Authoring and compilation API

```python
from typing import Annotated, Literal

import sqlrules
from pydantic import ConfigDict, Field, PositiveInt, StrictBool, StringConstraints
from sqlrules_postgresql import PostgresPlugin


class UserRules(sqlrules.RuleSchema):
    model_config = ConfigDict(strict=False)

    id: PositiveInt
    age: int | None = Field(ge=18)
    name: Annotated[str, StringConstraints(min_length=2)]
    status: Literal["active", "disabled"]
    verified: StrictBool


user = UserRules.model_validate({
    "id": "12",
    "age": "21",
    "name": "Ada",
    "status": "active",
    "verified": True,
})
data = user.model_dump()

compiler = sqlrules.Compiler(
    plugins=[PostgresPlugin(server_version=(16, 0))],
)
compiled = compiler.compile(UserRules, users)
matching_rows = users.select().where(*sqlrules.where(compiled))
failing_rows = users.select().where(*sqlrules.notwhere(compiled))
```

`RuleSchema` is a Pydantic v2 `BaseModel` subclass. SQLRules limits which fields,
types, constraints, and config options can be declared so every accepted class
can compile. It does not limit normal model use: instances support Pydantic
construction, `model_validate()`, `model_dump()`, validation errors, and
FastAPI request/response use. `model_validate()` applies the SQLRules scalar
conversion profile. This aligns Python input and SQL predicates where their
source types are observable; database storage, SQL NULL, and backend type
evidence can still create documented differences. `compile()` accepts a
`RuleSchema` class or a normalized schema; it does not accept a model instance
as a filter. `Annotated[T, Field(...)]` and assignment-style fields normalize
to the same immutable schema representation. The module-level
`sqlrules.compile()` accepts the same explicit plugin selection as `Compiler`;
it does no backend auto-discovery.

Use Pydantic's own declarations directly inside `RuleSchema`: `pydantic.Field`,
`ConfigDict`, strict aliases such as `StrictBool` and `StrictInt`, supported
built-in constrained aliases such as `PositiveInt`, and compatible metadata
inside `Annotated`. SQLRules' `Field` and `RuleConfig` remain available for
SQL-specific settings such as `column` and `allow_empty`; they are not required
for ordinary Pydantic constraints.

At class creation, normalize public Pydantic `FieldInfo` and recognized
`Annotated` metadata into the same immutable SQLRules field representation.
For 2.0, the translatable Pydantic subset includes numeric bounds and
`multiple_of`, string length and pattern constraints, strictness, and compatible
Literal/Enum domains, subject to each backend's capability matrix. The
corresponding `annotated_types` markers are accepted too. Accept
`StringConstraints` only for its SQL-translatable length and pattern settings;
normalization options such as whitespace stripping or case conversion need an
explicit SQL transform and are not implied by `StringConstraints` as a whole.
Aliases, defaults, titles, descriptions, and examples retain their normal model
behavior or descriptive metadata; aliases do not select database columns unless
the caller opts into alias mapping or supplies an explicit column map.

An explicit allowlist prevents arbitrary Pydantic metadata from being treated
as SQL by accident. Duplicate or conflicting constraints and unsupported
metadata fail class construction with the annotation/field location. Validator,
serializer, and custom-core-schema callbacks with no equivalent SQL rule are
not valid declarations on `RuleSchema`; a full Pydantic `BaseModel` can still
use them normally and the converter reports or removes them when producing a
`RuleSchema`.
[Pydantic fields and `Annotated` metadata](https://pydantic.dev/docs/validation/latest/concepts/fields/),
[strict aliases and `Strict`](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/),
and [Pydantic type aliases and constraints](https://pydantic.dev/docs/validation/latest/api/pydantic/types/) are the reference forms for this allowlist.

- Strictness precedence: explicit field setting, reusable type setting,
  inherited/declared `model_config`, then the lax default. Contradictory
  settings at the same level are declaration errors.
- Single schema inheritance and reusable annotated types ship in 2.0. An
  override replaces the inherited field definition while retaining its position;
  new fields append in declaration order. Multiple schema inheritance is deferred.
- Unknown field arguments, incompatible constraints, invalid constraint values
  (such as a nonpositive divisor or negative length), and arbitrary annotation
  metadata are errors. Forward references must resolve before a schema is
  finalized; unresolved or unsupported recursive types fail explicitly.
- Pydantic defaults and default factories apply when constructing or validating
  Python model instances. They never become equality predicates, SQL
  `COALESCE`, or exemptions from checking a bound database column. `ClassVar` is
  available for non-field class metadata.
- Custom Python validators, computed fields, and serializers without an
  equivalent SQL rule are outside the native rule subset and fail declaration
  validation. The Pydantic converter can remove them and report the change.
- Preserve title, description, and examples in 2.0 so later schema export can
  use them. Keep them separate from executable rules.
- Column resolution: explicit `column_map[field_name]`, then `Field(column=...)`,
  then the Python field name. Expressions in `column_map` need the same source
  type evidence as columns. Every type-only field requires a binding.

## Types, coercion, and observable storage

The initial scalar vocabulary is `bool`, `int`, `float`, `Decimal`, `str`,
`date`, `datetime`, `time`, and `UUID`, plus supported `Literal`, `Enum`, and
nullable forms. Existing dialect markers remain supported where a plugin can
establish the required container or range type. General unions and recursive
container validation arrive in later releases.

A backend capability is identified by source representation, target type,
strictness, operator, server version, and relevant database settings. Supporting
an annotation does not imply every possible source representation can be
translated on every database.

Strict mode uses the logical type observable in the database. It cannot recover
the Python type that existed before insertion. The 2.0 policy requires an exact
logical type match, including distinguishing integers from booleans and floats.
This follows the requested no-coercion rule. Pydantic itself has type-specific
strict exceptions, including accepting integers for float fields; adapter
reports must identify such semantic differences. [Pydantic conversion table](https://pydantic.dev/docs/validation/latest/concepts/conversion_table/)

Backend implementations must establish their type evidence:

| Source | Evidence and behavior |
|---|---|
| Database-enforced native column | Declared native type can establish the logical type when the supplied binding accurately describes the database. |
| SQLite value | Inspect runtime storage classes; a SQLAlchemy type or column affinity alone cannot prove each row's type. |
| Emulated bool/date/UUID representation | Require an explicit storage mapping and value checks; record the mapping in the compiled plan. If the required distinction is unavailable, raise a capability error. |
| JSON value | Preserve its type tag and distinguish a missing path, JSON null, and SQL NULL. |
| Unknown/custom SQLAlchemy type | Require a registered source adapter or explicit storage mapping. |

SQLite's flexible typing and emulated date/time storage motivate this distinction.
[SQLite datatypes](https://www.sqlite.org/datatype3.html)

Known incompatible data is a non-match, including a text value under strict
`int`. A known text column under strict `int` can therefore compile to false.
An inability to implement or determine the required semantics is a compile-time
capability error. Invalid row data should not cause a conversion exception.

Lax mode follows a versioned SQLRules conversion table informed by Pydantic's
Python-input behavior. Record the reference Pydantic versions and all intentional
differences. Python-input and JSON-input validation have different strict rules;
neither becomes an implicit SQL storage policy. [Pydantic strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/)

### Conversion acceptance criteria

Each supported conversion must define accepted lexical forms, numeric range,
precision, and normalized value. The conformance corpus includes signs, leading
zeros, whitespace, exponents, fractional values, overflow, NaN/infinity,
invalid calendar dates, time zones, Unicode, and collation-sensitive values.
Numeric-to-string conversion is not automatically enabled by lax mode.

Backend integer limits, exact decimal arithmetic, and time precision must be
explicit. An engine cast that truncates, rounds, saturates, or supplies a fallback
value is not sufficient evidence of validity. A regex matching a date's shape
does not establish calendar validity. SQLite documents that CAST can perform
lossy conversions. [SQLite CAST expressions](https://www.sqlite.org/lang_expr.html#castexpr)

Literal and Enum domains also pass through an explicit type/domain contract.
Avoid relying on database collation or implicit coercion to define membership;
mixed-type domains need type-tagged alternatives or an unsupported diagnostic.
Large or nonrepresentable constants fail explicitly rather than being rounded.
Patterns require an explicit matching/flag contract per backend. Unicode length,
trailing spaces, and case-sensitive membership belong in conformance fixtures;
selecting a familiar SQL function name does not establish equivalent behavior.

## Safe field evaluation and nulls

The backend prepares a field once as `PreparedValue(source, value, valid,
is_null, logical_type)`. `value` is a safe expression in the target type;
`valid` is a non-null boolean indicating successful type matching/conversion.
Bounds, lengths, patterns, and membership consume `value`.

The logical field rule is:

```text
if source is SQL NULL:
    return allow_none
return valid AND every_constraint(value)
```

This describes semantics, not a mandated SQL evaluation order. Preparation
must make every potentially failing conversion safe wherever the expression
is evaluated. `is_valid(source) AND CAST(source AS target)` is insufficient:
SQL optimizers can reorder boolean expressions. Use proven backend conversion
primitives or guarded expressions whose complete input domain is covered.
Do not assume wrapping arbitrary SQL in CASE is a universal safety guarantee.
[PostgreSQL expression evaluation](https://www.postgresql.org/docs/current/sql-expressions.html#SYNTAX-EXPRESS-EVAL)

For `age: int | None = Field(ge=18)`, the nullable branch wraps both type and
bound checks. A failed conversion producing NULL must remain distinguishable
from an original nullable value. Each final predicate returns true or false;
SQL UNKNOWN is normalized to false after explicit null handling. This makes
negation a defined complement: `sqlrules.notwhere(compiled)` selects every row
that fails at least one rule. It contains `~compiled.predicate`, so callers can
also use that expression directly. The root predicate combines all field rules
with AND before negation. Negating an individual field predicate, or negating a
raw SQL expression that can evaluate to UNKNOWN, does not provide the same
result. An explicitly allowed empty schema has a true root predicate and a
false negated predicate.

### Required behavioral examples

These examples refer to observed source types, before rule coercion:

| Source value/type | Lax `int, ge=18` | Strict `int, ge=18` |
|---|---|---|
| integer 20 | Match | Match |
| text "20" | Match where this conversion is supported | Non-match |
| text "9" | Non-match after numeric comparison | Non-match |
| text "bad" | Non-match without a SQL conversion error | Non-match |
| real 20.5 | Non-match; fractional values cannot become integers | Non-match |
| SQL NULL | Match only for the nullable annotation | Match only for the nullable annotation |

## Compiler and result architecture

```text
RuleSchema class ──────────────┐
                              v
Pydantic converter ──> immutable SchemaSpec + provenance
                              |
                         typed rule IR
                              |
              column binding + capability resolution
                              |
               prepared values + grouped predicates
                              |
                        CompiledRules
```

Internal typed expression and boolean group nodes belong in 2.0. They are
already needed for nullable fields and Literal/Enum domains; 2.1 exposes richer
public composition syntax. Preserve field identity, source location, semantic
profile, and adapter provenance through each stage.

`CompiledRules` replaces the bare dictionary at the 2.0 major boundary:

- `predicate`: the authoritative complete SQLAlchemy boolean expression. It
  has total true/false semantics on every row the backend supports.
- `fields`: immutable ordered field results, each containing its grouped
  predicate and binding/type information. They support inspection, not
  reconstruction of future cross-field logic.
- `diagnostics`: diagnostics belonging to this compilation result.
- `explain()`: a structured compile plan showing bindings, coercions,
  capabilities, and declared storage assumptions; it does no database EXPLAIN.
- `where(compiled)`: returns `[compiled.predicate]`, preserving the 1.x list
  shape and `.where(*sqlrules.where(...))` call style while keeping the full
  root group together. `flatten(compiled)` remains an alias for `where()`.
- `notwhere(compiled)`: returns `[~compiled.predicate]`, so
  `.where(*sqlrules.notwhere(compiled))` selects failures. It negates the root
  once, rather than negating each field or constraint separately. Callers that
  want a bare SQLAlchemy expression can use `compiled.predicate` or
  `~compiled.predicate` directly. No automatic conversion to a field dictionary
  loses model-level relationships.

In 1.x, `~sqlrules.where(rules)` raises `TypeError` because `where()` returns a
list. Wrapping that list in `and_(*where(rules))` still leaves SQL UNKNOWN for
nullable failures, so negation does not select every failing row. The 2.0 root
predicate must be total before `notwhere()` or direct `~compiled.predicate`
exposes its complement. A `notwhere()` helper over the 1.x rule dictionary
cannot provide this guarantee by simply negating its existing expressions.

Use immutable registry snapshots and per-call compilation state. Bound
SQLAlchemy expressions are never stored in shared schema IR. SQLRules does not
maintain a process-wide schema cache; it normalizes declarations per compile
so mutable marker payload changes cannot leave stale entries. Pydantic keeps
its own compiled model validators. Diagnostics must not leak between
concurrent compilations.

## Explicit Pydantic conversion

Ship the converter in `sqlrules.integrations.pydantic`. The current core
distribution already requires Pydantic v2, so the converter needs no optional
dependency extra or separate PyPI package.

```python
from sqlrules.integrations.pydantic import from_pydantic

conversion = from_pydantic(ApiModel, on_incompatible="warn")
RulesModel = conversion.model
instance = RulesModel.model_validate(input_data)
compiled = compiler.compile(RulesModel, users)
report = conversion.report
```

Conversion policies are `warn` (default: strip incompatible behavior and warn
about semantic changes), `drop` (strip and return the report), and `raise`
(reject semantic loss). These policies apply during conversion. Compilation of
the resulting schema always requires all retained rules to be supported.

The report distinguishes:

| Outcome | Meaning |
|---|---|
| Preserved | A type or rule has a defined SQLRules representation. |
| Metadata | Documentation retained, or instance/serialization behavior omitted with an explanation. |
| Dropped | An unsupported field or rule was removed. |
| Changed/unknown semantics | Strictness, normalization, or Python callbacks prevent a claim of equivalent validation. |

Each entry records field/model location, original feature, reason code,
replacement when applicable, and whether acceptance may broaden, narrow, or is
unknown. Dropping a before/plain/wrap validator can change the meaning of the
remaining type rule; the converter must not describe every omission as merely
loosening validation. It never executes validators, default factories, or
serializers to infer SQL.

Inspection covers field and model decorator validators and custom type hooks
as well as field metadata. Reading only `FieldInfo.metadata` cannot account for
all validation behavior. Unrecognized hook chains are reported as unknown.
Converted output is a generated `RuleSchema` model class, so its retained
fields can also be instantiated and validated with the SQLRules runtime API.

Preserve type-only fields and resolve field/model strictness. Drop a field when
its type cannot be represented; drop an individual incompatible constraint when
its remaining type and rules are still representable. Missing dialect support
is deferred to compilation, rather than dropping a representable marker.
Pydantic aliases are recorded for inspection; automatic column mapping uses
Python field names unless the caller explicitly supplies a mapping or opts into
a documented simple-alias mapping policy.

Reject conversion to an empty schema by default. An explicit `allow_empty=True`
converter argument permits a predicate that accepts every row and records that
decision. Directly declared empty schemas require `RuleConfig(allow_empty=True)`.

## Dialect and plugin contract

2.0 introduces plugin API version `2`. Separate source/type preparation from
constraint translation; predicate-only v1 translators cannot implement the new
coercion contract without adaptation. Existing marker names can remain stable
where their meaning is unchanged.

Require one explicitly selected backend provider, optionally accompanied by
constraint plugins. Core can normalize schemas without a backend; binding a
schema requires backend capabilities. The existing `dialect` string hint cannot
silently select behavior. Caller-supplied server versions and relevant settings
are recorded in the plan; compilation never probes a live connection. Version
dependent features require supplied information or a documented conservative
baseline. Any required connection helper must be declared explicitly.

Every backend publishes supported, unsupported, and mapping-required cases.
Expose capability inspection before binding and collect unsupported field paths
into an actionable compilation error. A known data mismatch compiles to a
non-match. Unsupported semantics never disappear under warn/ignore policies.

Before 2.0 implementation proceeds beyond prototypes, freeze a release matrix
for PostgreSQL, SQLite, MySQL, and SQL Server with actual supported server
versions. Each must support its native scalar baseline in lax and strict modes
where observable, nullable groups, the existing applicable operators, and a
documented nonempty set of useful coercions. The matrix must state emulated or
unavailable types explicitly. No all-types/all-dialects parity claim is made.

## Migration and release evidence

- Keep 1.x documentation labeled as the shipped contract while 2.0 is planned.
  At release, update application docs, examples, plugin docs, and package pins.
- Migrate `compile(PydanticModel, table)` to explicit conversion, then compile
  the resulting schema. Migrate dictionary consumers to `CompiledRules`.
- Preserve the `select(...).where(*sqlrules.where(compiled))` call shape.
  Document `select(...).where(*sqlrules.notwhere(compiled))` for failures and
  `~compiled.predicate` for callers that want a bare expression.
- Remove `emit_type_checks` from the new schema API; annotations always matter.
  Explain strictness, nullable bounds, and the new explicit backend requirement.
- Retain semantic fixtures for valid 1.x constraints and document intentional
  changes. Test accepted row sets on actual supported database versions,
  including malformed data and cases where unsafe casts previously failed.
- Use a pinned Pydantic reference to compare supported conversion cases and
  record SQL-specific differences. SQL rendering assertions supplement these
  execution checks; they cannot prove coercion safety.
- Include reference semantic tests for `model_validate()` and SQL predicates,
  backend execution tests that partition rows into matches and failures under
  `notwhere(compiled)` (including SQL NULL, invalid conversions, and allowed empty
  schemas), adapter reports, concurrent compilation, cache-compatibility checks,
  documentation builds, and wheel installation in release validation.
  Establish performance baselines in 2.0 and measure subsequent changes.

The 2.0.0 release freezes the semantic profile as well as public API and plugin
contracts. Later 2.x features are additive or explicitly enabled. A new coercion
must not silently widen existing query results under the 2.0 profile; behavior
fixes must be identified in release notes. All five existing distributions stay
versioned together. Update the release workflow and version checks for the 2.x
major pins.

## Features staged after 2.0

| Release | New capability | Foundation already required in 2.0 |
|---|---|---|
| 2.1.0 | Public all/any/not groups, scalar unions, cross-field rules | Grouped IR, total predicates, typed expressions, complete result predicate |
| 2.2.0 | Nested JSON, tagged unions, collection length and item rules | Source adapters, explicit type evidence, null handling, backend capabilities |
| 2.3.0 | Named transforms, custom type mappings, schema export, SQL expression counterparts | Prepared values, metadata, provenance, stable extension contract |

Arbitrary Python callback translation and transparent mutation of database
values remain outside this compiler contract. Native rule models use Pydantic's
runtime model interface, but only the declared SQLRules subset is accepted;
serialization never changes database values or the compiled predicate.
Additional Pydantic features require a declared SQL meaning before they enter a
release.

# SQLRules Design Decisions

SQLRules 2.0 compiles an intentionally limited subset of Pydantic model
declarations into SQL predicates. These decisions define the semantic contract
for the 2.x series.

## 1. Rule schemas remain Pydantic models

`RuleSchema` is a `pydantic.BaseModel` subclass. Instances keep normal Pydantic
validation, serialization, JSON Schema, and framework integration behavior.
SQLRules limits the declarations inside a RuleSchema to the types, constraints,
and compatible metadata that it can compile; it does not restrict how callers
instantiate or use the model.

Compatible Pydantic imports work directly in class declarations. SQLRules adds
`Field(column=...)` and `RuleConfig` for database binding and SQL-specific
options. Unrestricted Pydantic models can be passed through `from_pydantic()`;
conversion returns another Pydantic model and a report for removed semantics.

## 2. Type annotations always create row rules

Every scalar annotation contributes a predicate, even without an explicit
constraint. Lax mode is the default and follows the documented SQLRules
coercion profile. `strict=True`, `ConfigDict(strict=True)`, and compatible
strict metadata require the observed database value to have the declared
logical type. Strictness and supported constraints are inspectable on the
compiled plan.

The database cannot recover the Python object originally supplied to an ORM.
SQLRules therefore defines types in terms of database storage evidence and
documents backend differences, including representations it cannot prove.

## 3. Prepare values safely before applying constraints

An explicit backend provider prepares each source column into a logical value,
validity predicate, NULL state, and capability description. Constraints run
against the prepared value. Invalid coercions are non-matches. Conversion
safety cannot depend on SQL evaluation order or short-circuiting.

If a provider cannot prove that a mapping or conversion is safe, compilation
raises `CapabilityError`. A known row-level type mismatch is a false predicate
instead. The capability matrix is part of the public semantic contract.

## 4. Every retained declaration must be enforced

Unsupported declarations on a RuleSchema raise during class construction or
compilation. Unsupported retained constraints never produce warnings or get
silently dropped. `from_pydantic()` is the explicit conversion boundary for
dropping incompatible behavior, and its report records what changed.

## 5. Compile predicates, not queries

SQLRules creates SQLAlchemy boolean expressions and never opens a connection,
inspects live database metadata, renders SQL strings, or executes statements.
Applications compose the result into Core or ORM queries.

`CompiledRules` contains a total root predicate, per-field results,
diagnostics, backend assumptions, and conversion provenance. `where()` returns
the root predicate in a list for spread-style SQLAlchemy calls. `notwhere()`
returns its complement. SQL NULL, invalid conversions, and failed constraints
are partitioned by those two helpers.

## 6. Backend selection is explicit

Exactly one backend provider prepares source values for a bind. Constraint
plugins may add translators, but cannot silently substitute source coercion
semantics. Server versions and collation or storage assumptions are explicit
and appear in capabilities or the compiled explain plan.

## 7. Reuse normalized declarations without global model caches

`Compiler.compile_model()` and `bind()` expose normalization and table binding
as separate operations. Normalized schema metadata is immutable. SQLRules does
not keep process-wide model-class cache entries; table-bound predicates are
created for the supplied columns. Legacy cache arguments remain inert
compatibility shims in 2.0.

## 8. Version semantics, not just syntax

The supported Pydantic declaration subset, coercion rules, backend evidence,
NULL behavior, and unsupported cases are versioned. New 2.x phases can add
features, but must preserve the acceptance behavior of existing schemas unless
a deliberate compatibility change is documented.

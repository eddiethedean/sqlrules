# Architecture

SQLRules compiles an immutable RuleSchema description into one total SQL
predicate. The compiler does not connect to a database or execute statements.

~~~text
RuleSchema class
    ↓
Pydantic declaration validation → immutable SchemaSpec
    ↓
backend provider: source type evidence and safe PreparedValue
    ↓
constraint translators → grouped field predicates
    ↓
CompiledRules.predicate → where() / notwhere()
~~~

## Declaration normalization

RuleSchema subclasses Pydantic BaseModel. Class creation checks supported
scalar types, nullability, strictness, Pydantic Field metadata, Annotated
markers, model configuration, and SQLRules column bindings. The resulting
SchemaSpec preserves source order, runtime metadata, constraints, and
conversion provenance. Unsupported Python-only callbacks and incompatible
declarations fail before a compiler is constructed.

Unrestricted Pydantic classes enter through from_pydantic(). The converter
returns a generated RuleSchema and a report of retained rules, metadata, and
removed or changed behavior. It never executes validators, serializers, or
default factories.

## Backend preparation

The caller selects exactly one BackendProvider. It receives a bound source
column and normalized RuleField, reports its versioned capabilities, and
returns PreparedValue:

- source: original bound column expression.
- value: safe normalized SQL expression for constraints.
- valid: non-null boolean for supported type/coercion behavior.
- is_null: whether the original source is SQL NULL.
- logical_type, coercion, capability: explain-plan evidence.

Known row mismatches become false. Missing type evidence or unsafe conversions
raise CapabilityError during compilation. The provider must not rely on a
separate boolean expression to guard a potentially failing CAST.

## Predicate assembly

Each field combines its null branch, type validity, and all constraints into
one group. Field groups combine under one root AND. Every predicate is
normalized from SQL UNKNOWN to false, so notwhere() is a complete complement
of where().

CompiledRules retains the root predicate, ordered field results, compile-local
diagnostics, backend version, assumptions, and explain() output. It contains
table-bound expressions and is never stored in a process-wide cache.

## Concurrency and caches

Each compile has a local diagnostics collector and context. Compiler instances
hold private immutable registry snapshots; callers can inspect a copy of the
registry. SQLRules does not maintain a global mutable schema cache. RuleSchema
classes retain Pydantic's own compiled validators, while SQLRules normalizes
the field declarations per compile.

See [COMPILER](COMPILER.md), [IR_CONTRACT](IR_CONTRACT.md), and
[TYPE_SUPPORT](TYPE_SUPPORT.md).

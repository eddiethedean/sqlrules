# FAQ

## What does SQLRules return?

Compiler.compile() returns CompiledRules, including the total root predicate,
ordered field results, compile diagnostics, and a structured explain plan.
where(compiled) and notwhere(compiled) return one-item lists for spread-style
SQLAlchemy WHERE calls.

## Does SQLRules validate request data?

RuleSchema is a normal Pydantic model and supports model_validate(),
model_dump(), and FastAPI integration. SQLRules compilation uses its field
declarations to query database rows; it does not turn an instance value such
as age=25 into a database equality predicate.

## How do I use a full Pydantic model?

Call sqlrules.integrations.pydantic.from_pydantic(). It returns a generated
RuleSchema and a report describing unsupported Python-only behavior that was
removed or changed. Direct compile of an unrestricted BaseModel is rejected.

## Why does a plain type annotation compile?

Every scalar annotation is a rule. Lax mode checks supported backend
conversions; strict mode checks the observable database logical type.
Optional fields allow SQL NULL.

## Why do I need a backend plugin?

Backend providers establish source type evidence, safe coercions, dialect
capabilities, and the versioned support profile. Select exactly one provider
when compiling. The compiler does not inspect a connection or infer a dialect
from the SQLAlchemy expression.

## What is dialect= on Compiler?

It is an optional assertion against the provider name. It does not select or
load a provider.

## How do I bind renamed columns?

Use column_map keyed by the Python field name or SQLRules Field(column=...).
Pydantic aliases keep their usual runtime behavior but do not bind columns.

## Can notwhere() return every failing row?

Yes. SQLRules normalizes field and root predicates so they do not produce SQL
UNKNOWN. notwhere(compiled) returns the total complement of the complete
root predicate.

## Where are type and dialect limitations documented?

See [TYPE_SUPPORT](../TYPE_SUPPORT.md), [DIALECT_SUPPORT](../DIALECT_SUPPORT.md),
and [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md).

## More help

[Troubleshooting](troubleshooting.md) · [Errors](../ERRORS.md) ·
[Getting started](getting-started.md)

# Constraint Reference

Every supported scalar annotation creates a type rule. Supported Pydantic
constraints add value rules that run against the backend-prepared expression.
The full source-type matrix is in [TYPE_SUPPORT](TYPE_SUPPORT.md).

## Portable operators

| Declaration | Rule |
|---|---|
| gt / ge / lt / le | Comparison after type preparation |
| multiple_of | Modulo equality where the backend has safe numeric modulo semantics |
| min_length / max_length | Backend length comparison |
| Literal[...] | Membership in the homogeneous literal domain |
| Enum | Membership in the enum value domain |
| pattern | Pattern match when the selected plugin implements it |

Portable translators are registered by core for comparisons, multiple_of,
length, and domain membership. Pattern requires a backend translator. The
built-in `multiple_of` translator raises `CapabilityError` for floating-point
fields, float divisors, and SQLite non-integral `Decimal` divisors. A plugin
can replace that translator with an implementation suited to its backend.

~~~python
from typing import Annotated
from pydantic import Field, StringConstraints
from sqlrules import RuleSchema


class UserRules(RuleSchema):
    age: int = Field(ge=18, le=120)
    name: Annotated[str, StringConstraints(min_length=2, max_length=80)]
~~~

Constraints are checked during class creation. Duplicate operators,
contradictory bounds, invalid divisors, negative lengths, and unsupported
field/constraint combinations fail before compilation.

## Strictness and nullability

Use Field(strict=True), a Pydantic strict alias, or model_config strict=True to
require an exact observable database logical type. The default is lax mode;
its supported conversions are listed per backend in TYPE_SUPPORT.

An annotation such as int | None accepts SQL NULL. The nullable branch wraps
both type validity and constraints. Non-nullable fields reject SQL NULL even
when they have a default in Python.

## Dialect markers

Import SQL-only markers from sqlrules.markers or sqlrules:

- JsonContains / JsonHasKey
- ArrayContains / ArrayOverlap
- RangeContains / RangeOverlap
- FullTextMatch

Markers need one backend plugin that supports the source SQL type and
operator. A marker does not add nested item validation or validate a Pydantic
collection value against every database element.

## Result helpers

~~~python
compiled = compiler.compile(UserRules, users)
matches = users.select().where(*sqlrules.where(compiled))
fails = users.select().where(*sqlrules.notwhere(compiled))
~~~

where() and flatten() return one complete predicate. notwhere() returns its
total complement. See [IR_CONTRACT](IR_CONTRACT.md) for the result shape.

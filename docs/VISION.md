# Vision

SQLRules compiles SQL-compatible rule declarations into SQLAlchemy predicates.
The 2.x contract makes SQLRules-owned rule schemas the primary input, with
explicit conversion from unrestricted Pydantic models.

Native rule schemas remain Pydantic v2 models: users can instantiate them,
validate and serialize data, and use them in FastAPI. SQLRules restricts the
declarations inside a rule model to types and constraints it can compile. A
full Pydantic model stays usable as-is; conversion produces a restricted model
and reports any behavior it removes or changes.

In 2.0, annotations are active type rules, lax coercion is the default, and
strict mode requires the declared logical type. Compilation exposes its
bindings and conversion assumptions; a Pydantic conversion report explains
any behavior removed or changed. The semantic contract is described in
[the 2.0 design](V2_DESIGN.md), with delivery gates in [Milestones](MILESTONES.md).

## Goals

- Extremely small API
- Deterministic output
- Zero database dependency
- SQLAlchemy Core first
- ORM compatible

## North star

```python
compiled = compiler.compile(UserRules, users)
matching = select(users).where(*sqlrules.where(compiled))
failing = select(users).where(*sqlrules.notwhere(compiled))
```

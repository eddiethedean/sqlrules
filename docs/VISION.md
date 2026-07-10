# Vision

SQLRules is a tiny compiler that bridges Pydantic model constraints and
SQLAlchemy WHERE expressions.

## Goals

- Extremely small API
- Deterministic output
- Zero database dependency
- SQLAlchemy Core first
- ORM compatible

## North star

```python
rules = sqlrules.compile(UserFilter, users)
stmt = select(users).where(*sqlrules.where(rules))
```

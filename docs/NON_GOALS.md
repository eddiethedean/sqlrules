# Non-goals

SQLRules will not become or include:

- An ORM
- SQL string generation
- Runtime validation
- Database connectivity
- Query execution
- Migrations
- Automatic dialect detection
- Silent approximation of unsupported constraints

Applications remain responsible for composing queries, choosing dialects,
and executing SQL through SQLAlchemy.

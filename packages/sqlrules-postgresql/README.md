# sqlrules-postgresql

PostgreSQL dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

Registers a `pattern` translator using PostgreSQL's `~` operator.

```python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
rules = compiler.compile(MyModel, table)
```

Requires SQLRules 0.3.x. Applications remain responsible for using a
PostgreSQL-compatible SQLAlchemy dialect when executing queries.

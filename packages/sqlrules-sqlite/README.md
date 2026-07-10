# sqlrules-sqlite

SQLite dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

Registers a `pattern` translator using SQLite's `REGEXP` operator.

```python
from sqlrules import Compiler
from sqlrules_sqlite import SQLitePlugin

compiler = Compiler(plugins=[SQLitePlugin()], dialect="sqlite")
rules = compiler.compile(MyModel, table)
```

**Note:** SQLite does not enable `REGEXP` by default. Applications must
register a REGEXP function on the connection (for example via
`create_function`) before executing queries that use these expressions.

Requires SQLRules 0.3.x.

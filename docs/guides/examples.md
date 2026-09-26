# Examples

Runnable scripts live in the GitHub
[`examples/`](https://github.com/eddiethedean/sqlrules/tree/main/examples)
directory.

:::{dropdown} Setup: install the example dependencies

```bash
pip install "sqlrules>=2,<3" "sqlrules-sqlite>=2,<3"
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
python examples/postgresql_pattern.py
```

From a clone (contributors): `make install` then `make examples`.
:::

The [example README](https://github.com/eddiethedean/sqlrules/blob/main/examples/README.md)
shows the captured stdout from all three scripts. Those outputs are compiled
SQLAlchemy `SELECT` statements; no database is contacted.

## Next

- [Getting started](getting-started.md)
- [ORM / column_map](orm-column-map.md)
- [Markers](markers.md)
- [Upgrade from 0.x](upgrade-0x.md)

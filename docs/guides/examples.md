# Examples

Runnable scripts live in the GitHub
[`examples/`](https://github.com/eddiethedean/sqlrules/tree/main/examples)
directory.

## Run them

```bash
pip install "sqlrules>=2,<3" "sqlrules-sqlite>=2,<3"
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
python examples/postgresql_pattern.py
```

From a clone (contributors): `make install` then `make examples`.

| Script | Shows |
|---|---|
| `basic_compile.py` | Core `compile` + `where` |
| `select_usage.py` | `Literal` + compiled `select()` |
| `postgresql_pattern.py` | Why `pattern` needs a plugin, then Postgres fix |

Expected shape: printed field names and a `SELECT` with bound parameters.

## Next

- [Getting started](getting-started.md)
- [ORM / column_map](orm-column-map.md)
- [Markers](markers.md)
- [Upgrade from 0.x](upgrade-0x.md)

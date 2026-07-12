# Examples

Runnable scripts for SQLRules.

## From PyPI

```bash
pip install "sqlrules>=1,<2"
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules[postgresql]"
python examples/postgresql_pattern.py
```

## From this repository (contributors)

```bash
make install
make examples
```

| Script | Shows | Expected output (shape) |
|---|---|---|
| `basic_compile.py` | Core `compile` + `where` | `fields: ['age', 'name']` then a `SELECT` |
| `select_usage.py` | `Literal` + compiled `select()` | printed `SELECT` with `IN` / comparisons |
| `postgresql_pattern.py` | Why `pattern` needs a plugin, then Postgres fix | first compile raises; second prints rules |

Application users should install from **PyPI**, not from `packages/`.

# Examples

Runnable scripts for SQLRules.

## From PyPI

```bash
pip install "sqlrules>=2,<3" "sqlrules-sqlite>=2,<3"
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules-postgresql>=2,<3"
python examples/postgresql_pattern.py
```

## From this repository (contributors)

```bash
make install
make examples
```

| Script | Shows | Expected output (shape) |
|---|---|---|
| `basic_compile.py` | RuleSchema + SQLite provider + `where` | field names then a `SELECT` |
| `select_usage.py` | `Literal` + compiled `select()` | printed `SELECT` with `IN` / comparisons |
| `postgresql_pattern.py` | PostgreSQL pattern and JSON markers | prints a `SELECT` with dialect operators |

Application users should install from **PyPI**, not from `packages/`.

# Examples

Runnable scripts for SQLRules.

## From this repository (recommended while developing)

```bash
make install
make examples
# or individually:
python examples/basic_compile.py
python examples/select_usage.py
python examples/postgresql_pattern.py
```

## From PyPI (1.0+)

```bash
pip install "sqlrules>=1,<2"
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules[postgresql]"
python examples/postgresql_pattern.py
```

If `pip show sqlrules` reports a version below 1.0.0, or dialect packages are
missing on PyPI, use **from this repository** above.

| Script | Shows | Expected output (shape) |
|---|---|---|
| `basic_compile.py` | Core `compile` + `where` | `fields: ['age', 'name']` then a `SELECT` |
| `select_usage.py` | `Literal` + compiled `select()` | printed `SELECT` with `IN` / comparisons |
| `postgresql_pattern.py` | Why `pattern` needs a plugin, then Postgres fix | first compile raises; second prints rules |

Application users should install from **PyPI** once 1.0+ is published, not
from `packages/`.

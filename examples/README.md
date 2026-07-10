# Examples

Runnable scripts for SQLRules. From the repo root:

```bash
pip install sqlrules
python examples/basic_compile.py
python examples/select_usage.py

pip install "sqlrules[postgresql]"
python examples/postgresql_pattern.py
```

| Script | Shows |
|---|---|
| `basic_compile.py` | Core `compile` + `where` |
| `select_usage.py` | `Literal` + compiled `select()` |
| `postgresql_pattern.py` | Why `pattern` needs a plugin, then Postgres fix |

Application users should install from **PyPI**, not from `packages/`.

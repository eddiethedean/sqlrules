.PHONY: install test docs dist check examples

install:
	python -m pip install -e ".[dev,docs]"
	python -m pip install -e packages/sqlrules-postgresql \
	  -e packages/sqlrules-sqlite \
	  -e packages/sqlrules-mysql \
	  -e packages/sqlrules-mssql

test:
	ruff check .
	ruff format --check .
	mypy src/sqlrules
	mypy --disable-error-code=redundant-cast \
	  packages/sqlrules-postgresql/src packages/sqlrules-sqlite/src \
	  packages/sqlrules-mysql/src packages/sqlrules-mssql/src
	python scripts/check_versions.py
	pytest tests \
	  packages/sqlrules-postgresql/tests \
	  packages/sqlrules-sqlite/tests \
	  packages/sqlrules-mysql/tests \
	  packages/sqlrules-mssql/tests

docs:
	sphinx-build -W -b html docs docs/_build/html

dist:
	rm -rf dist dist-plugins
	python -m build
	python -m build packages/sqlrules-postgresql --outdir dist-plugins
	python -m build packages/sqlrules-sqlite --outdir dist-plugins
	python -m build packages/sqlrules-mysql --outdir dist-plugins
	python -m build packages/sqlrules-mssql --outdir dist-plugins
	twine check dist/* dist-plugins/*

check: test docs

examples:
	python examples/basic_compile.py
	python examples/select_usage.py
	python examples/postgresql_pattern.py

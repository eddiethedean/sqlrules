# Security

## Trust model

SQLRules is a pure compiler. It does not connect to databases or execute
SQL. Security boundaries are:

1. **Installed Python packages** — dialect plugins and custom
   `SQLRulesPlugin` objects run arbitrary Python in
   `register(registry)` at `Compiler` construction. Install only trusted
   plugins. There is no sandbox.
2. **Constraint values** — translated into SQLAlchemy expressions with
   bound parameters (not string-built SQL). Classic SQL injection via
   constraint values is not a practical risk when using the public API.
3. **Patterns / REGEXP / full-text** — pattern strings and full-text
   queries are bound as parameters, but evaluation cost is
   engine-dependent. Untrusted `Field(pattern=...)` or
   `FullTextMatch(...)` values can cause **CPU denial of service**
   (ReDoS / expensive regex), not injection. Treat patterns from
   untrusted input as a cost-control problem.

### Pattern / REGEXP cost (elevated)

| Surface | Risk |
|---|---|
| PostgreSQL `~` / `~*` | Engine-side regex cost |
| MySQL `REGEXP` | Engine-side regex cost |
| SQLite `REGEXP` via `sqlrules_sqlite.register_regexp` | **Python `re.search` per row** in-process — catastrophic backtracking can stall the application worker |

**Recommendations**

- Prefer **static / allowlisted** patterns authored with the model, not
  patterns taken from end-user input.
- Do not expose free-form regex from untrusted clients on hot query paths.
- For SQLite, understand that `register_regexp` is not a sandbox; it runs
  Python's `re` in your process.
- Official dialect packages are released in lockstep with core — pin the
  same major line (`sqlrules>=1,<2` and matching dialect extras).

## Non-goals

SQLRules will not provide a plugin capability system, bytecode sandbox,
or automatic dialect detection. See [NON_GOALS.md](NON_GOALS.md).

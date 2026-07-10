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

## Recommendations

- Prefer official packages under `packages/` or audited plugins.
- Do not pass untrusted regular expressions into model constraints in
  hot paths without limits.
- Applications remain responsible for SQLAlchemy execution, connection
  security, and authorization.

## Non-goals

SQLRules will not provide a plugin capability system, bytecode sandbox,
or automatic dialect detection. See [NON_GOALS.md](NON_GOALS.md).

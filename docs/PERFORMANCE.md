# SQLRules Performance

Compilation builds SQLAlchemy expression objects only. It does not connect to
a database, inspect live schema metadata, render SQL strings, or execute a
query. Work should scale approximately with the number of declared fields and
constraints.

## Pipeline costs

`Compiler.compile_model()` validates and normalizes a `RuleSchema` into an
immutable `SchemaSpec`. `Compiler.bind()` resolves its columns, prepares source
expressions through one backend provider, translates constraints, and creates
the final predicate and explain plan. Schema normalization and table binding
are measured separately by the benchmark.

SQLRules does not keep a process-wide model cache. The `cache` constructor
argument and `clear_model_cache()` function are compatibility shims and do not
enable or clear a cache. Compiled predicates remain bound to the SQLAlchemy
columns used to create them; applications should reuse a predicate only with
the table or alias it was compiled against.

## Benchmark

Run the representative local benchmark with:

```bash
python -m benchmarks.bench_compile
```

It measures normalization, bind/compile, and full compile for schemas with 5,
25, and 100 fields. The script reports best-of-repeat timings; its numbers are
diagnostic baselines, not CI thresholds. Run it on the same Python, SQLAlchemy,
hardware, and plugin versions when comparing changes.

The benchmark intentionally does not imply a cache benefit or promise fixed
latency targets. SQLRules 2.0 establishes the measurement method; later 2.x
performance work can add stable CI thresholds after representative baselines
are collected.

## Design guidance

- Measure before optimizing and profile the stage that accounts for the cost.
- Keep schema and plan metadata immutable where practical.
- Avoid database I/O and dialect guessing in compilation.
- Keep provider conversion expressions safe if the database evaluates
  predicates in a different order.
- Prefer straightforward linear passes over speculative caches or persistent
  state.

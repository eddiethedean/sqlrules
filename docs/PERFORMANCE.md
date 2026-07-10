# SQLRules Performance

## Purpose

This document defines the performance goals, optimization strategy, and
benchmarking methodology for SQLRules.

The compiler should be fast enough that users rarely need to think about
its cost. Compilation should be deterministic, lightweight, and suitable
for use during application startup or on demand.

------------------------------------------------------------------------

# Performance Goals

## Primary Goals

-   Low latency compilation
-   Zero database I/O
-   Minimal memory allocations
-   Deterministic execution
-   Linear scalability with respect to model size

Target complexity:

-   **Time:** O(fields + constraints)
-   **Memory:** O(fields + constraints)

------------------------------------------------------------------------

# Compiler Pipeline

``` text
Model
 │
 ▼
Inspect
 │
 ▼
Extract Constraints
 │
 ▼
Build IR
 │
 ▼
Translate
 │
 ▼
Assemble Rules
```

Each stage should process data in a single pass where practical.

------------------------------------------------------------------------

# Expected Workload

Typical models:

    Fields   Constraints
  -------- -------------
         5            10
        20            40
       100           200

Compilation should scale approximately linearly.

------------------------------------------------------------------------

# Caching

## Metadata Cache

Cache expensive model introspection (Phase 1).

Key:

``` python
model_class
```

Cached values:

-   field descriptors
-   extracted constraints
-   normalized `ModelIR`

Avoid caching SQLAlchemy column objects, which are table-specific.

Enabled by default (`cache=True`). Thread-safe via a lock-guarded
``dict`` keyed by model class. Entries are **strong** references for the
process lifetime (``ModelIR`` retains the model type). Call
``ModelIRCache.clear()`` when creating many ephemeral models.

------------------------------------------------------------------------

## Translator Cache

Translator lookup should be O(1).

Use dictionary-based dispatch keyed by constraint operator.

``` python
{
    "ge": GreaterEqualTranslator(),
    "min_length": MinLengthTranslator(),
}
```

------------------------------------------------------------------------

# Memory Strategy

Prefer immutable lightweight objects.

Recommendations:

-   dataclasses with `slots=True`
-   tuples instead of mutable lists where appropriate
-   avoid deep copies
-   reuse immutable compiler state

------------------------------------------------------------------------

# Allocation Strategy

Avoid:

-   repeated metadata parsing
-   duplicate constraint objects
-   unnecessary intermediate collections

Prefer generators internally when they improve readability without
sacrificing determinism.

------------------------------------------------------------------------

# SQLAlchemy Interaction

SQLRules should only construct SQLAlchemy expression objects.

It must never:

-   connect to a database
-   compile SQL strings
-   inspect database metadata
-   execute queries

This keeps runtime predictable.

------------------------------------------------------------------------

# Benchmark Suite

Representative benchmarks live in `benchmarks/bench_compile.py`:

```bash
python -m benchmarks.bench_compile
```

Sizes:

-   Small model (5 fields)
-   Medium model (25 fields)
-   Large model (100+ fields)

Measure:

-   wall-clock compilation time (cold vs warm cache)
-   cache hit benefit

Illustrative latency targets (not CI-gated):

-   Small model cold compile on the order of sub-millisecond to a few ms
-   Medium model under a few milliseconds when warm

CI does **not** currently enforce performance regression gates. Formal
gates remain a post-1.0 / performance-milestone item.

------------------------------------------------------------------------

# Profiling

Use profiling to identify:

-   repeated introspection
-   unnecessary allocations
-   slow translator implementations

Optimize only after profiling demonstrates a measurable benefit.

------------------------------------------------------------------------

# Concurrency

The compiler should be safe for concurrent reads after initialization.

Recommendations:

-   immutable compiler configuration
-   read-only translator registry
-   thread-safe caches where applicable

------------------------------------------------------------------------

# Future Optimizations

Potential improvements:

-   incremental compilation
-   persistent metadata caches
-   plugin cache integration
-   ahead-of-time IR generation
-   optional C/Rust acceleration for metadata extraction

------------------------------------------------------------------------

# Performance Targets

Illustrative goals on modern hardware:

  Model Size     Target Compile Time
  ------------ ---------------------
  Small                    \< 0.5 ms
  Medium                     \< 2 ms
  Large                     \< 10 ms

Exact values should be validated through continuous benchmarking.

------------------------------------------------------------------------

# Testing

Local benchmarks: `python -m benchmarks.bench_compile`.

CI performance regression gates are **not** enabled yet; treat the
latency table above as illustrative until a post-1.0 performance
milestone adds them.

------------------------------------------------------------------------

# Design Principles

-   Measure before optimizing
-   Optimize the common case
-   Keep algorithms simple
-   Favor deterministic performance
-   Preserve readability over micro-optimizations

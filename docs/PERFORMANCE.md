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

Cache expensive model introspection.

Suggested key:

``` python
(model_class, compiler_options)
```

Cached values:

-   field descriptors
-   extracted constraints
-   normalized IR

Avoid caching SQLAlchemy column objects, which are table-specific.

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

Representative benchmarks:

-   Small model (5 fields)
-   Medium model (25 fields)
-   Large model (100+ fields)

Measure:

-   wall-clock compilation time
-   allocations (where feasible)
-   cache hit rate
-   translator dispatch cost

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

Performance regression tests should run in CI.

Track:

-   compile latency
-   memory usage trends
-   cache effectiveness

Reject regressions that significantly exceed established baselines.

------------------------------------------------------------------------

# Design Principles

-   Measure before optimizing
-   Optimize the common case
-   Keep algorithms simple
-   Favor deterministic performance
-   Preserve readability over micro-optimizations

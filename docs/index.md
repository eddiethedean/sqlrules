# SQLRules documentation

```{raw} html
<div class="sr-hero">
  <div class="sr-hero-badges">
    <span class="sr-badge sr-badge--accent">v{{ release }}</span>
    <span class="sr-badge">Pydantic → SQLAlchemy</span>
    <span class="sr-badge">Python {{ python_requires }}</span>
  </div>
  <p class="sr-hero-kicker">SQLRules documentation</p>
  <p class="sr-hero-title">Compile constraints into WHERE rules</p>
  <p class="sr-lead">SQLRules turns a safe subset of Pydantic field constraints into deterministic SQLAlchemy expressions—one package, no database connection, plugins for dialect operators.</p>
  <p>
    <a class="sr-hero-cta" href="guides/getting-started.html">Get started →</a>
    <a class="sr-hero-cta sr-hero-cta--secondary" href="guides/start-here.html" style="margin-left:0.75rem">Choose a path</a>
  </p>
</div>
```

Pick the path that matches how you work:

::::{grid} 2
:gutter: 3

:::{grid-item-card} Application developers
:link: guides/getting-started
:link-type: doc

**Compile filters from models.** Install `sqlrules`, map a Pydantic model to a table, and pass `where(rules)` into SQLAlchemy.

+++
**Open getting started →**
:::

:::{grid-item-card} Plugin authors
:link: PLUGIN_SYSTEM
:link-type: doc

**Extend the compiler.** Register dialect translators for regex, JSON, arrays, and custom operators with a versioned plugin API.

+++
**Open plugin system →**
:::

::::

::::{grid} 2
:gutter: 3

:::{grid-item-card} Evaluating SQLRules
:link: guides/design-philosophy
:link-type: doc

**Fit and non-goals.** What SQLRules is, what it refuses to do, and how the API tiers stay stable.

+++
**Read design philosophy →**
:::

:::{grid-item-card} API reference
:link: reference/index
:link-type: doc

**Contracts and autodoc.** Narrative API tiers plus generated members from the installed package.

+++
**Open reference →**
:::

::::

:::{admonition} Not a query builder
:class: note

SQLRules does not connect to a database, generate SQL strings, or validate request payloads at runtime. It only compiles supported constraints into expressions. See [design philosophy](guides/design-philosophy.md).
:::

```{raw} html
<div class="sr-callout">
  <strong>Install:</strong> <code>pip install sqlrules</code>
  — optional dialects via <code>pip install sqlrules-postgresql</code> (or sqlite / mysql / mssql).
</div>
```

(documentation-map)=
## Documentation map

```{toctree}
:maxdepth: 1
:caption: Getting started

guides/start-here
guides/getting-started
guides/design-philosophy
```

:::{admonition} Questions?
:class: tip

See the [FAQ](guides/faq.md) or [troubleshooting](guides/troubleshooting.md).
:::

```{toctree}
:maxdepth: 1
:caption: FAQ and troubleshooting

guides/faq
guides/troubleshooting
```

```{toctree}
:maxdepth: 1
:caption: Guides

SPEC
CONSTRAINTS
PLUGIN_SYSTEM
TYPE_SUPPORT
DIALECT_SUPPORT
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/index
reference/glossary
reference/autodoc
API
ERRORS
SECURITY
```

```{toctree}
:maxdepth: 1
:caption: Architecture

ARCHITECTURE
COMPILER
TRANSLATORS
INTERNAL_API
TESTING
PERFORMANCE
```

```{toctree}
:maxdepth: 1
:caption: Design

VISION
PHILOSOPHY
NON_GOALS
DESIGN_DECISIONS
```

```{toctree}
:maxdepth: 1
:caption: Project

project/roadmap
MILESTONES
project/changelog
project/contributing
```

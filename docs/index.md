# SQLRules documentation

```{raw} html
<div class="sr-hero">
  <div class="sr-hero-badges">
    <span class="sr-badge sr-badge--accent">v{{ release }}</span>
    <span class="sr-badge">Pydantic → SQLAlchemy</span>
    <span class="sr-badge">Python {{ python_requires }}</span>
  </div>
  <p class="sr-hero-kicker">Pydantic RuleSchema → SQLAlchemy predicates</p>
  <p class="sr-hero-title">Compile rules into total predicates</p>
  <p class="sr-lead">SQLRules validates RuleSchema models with Pydantic, then compiles their supported declarations through one explicit backend. It performs no database I/O and returns both matching and failing-row predicates.</p>
  <p>
    <a class="sr-hero-cta" href="guides/start-here.html">Start here →</a>
    <a class="sr-hero-cta sr-hero-cta--secondary" href="guides/getting-started.html" style="margin-left:0.75rem">Getting started</a>
  </p>
</div>
```

Pick the path that matches how you work:

::::{grid} 2
:gutter: 3

:::{grid-item-card} Application developers
:link: guides/getting-started
:link-type: doc

**Compile supported schemas.** Define a RuleSchema, select a backend provider, and pass where(compiled) or notwhere(compiled) into SQLAlchemy.

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

SQLRules does not connect to a database or generate SQL strings. RuleSchema
is still a normal Pydantic model, but the compiler uses the schema's rules to
select matching database rows. See
[design philosophy](guides/design-philosophy.md).
:::

```{raw} html
<div class="sr-callout">
  <strong>Install:</strong> <code>pip install "sqlrules&gt;=2,&lt;3"</code>
  — add the matching dialect package from the same 2.x line.
  <code>pattern</code> needs a dialect plugin.
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
:caption: How-to guides

guides/examples
guides/orm-column-map
guides/markers
guides/upgrade-0x
guides/upgrade-1x
guides/faq
guides/troubleshooting
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/index
SPEC
CONSTRAINTS
TYPE_SUPPORT
DIALECT_SUPPORT
PLUGIN_SYSTEM
API
IR_CONTRACT
ERRORS
SECURITY
reference/glossary
reference/application
reference/plugin-api
```

```{toctree}
:maxdepth: 1
:caption: Internals

internals/index
ARCHITECTURE
COMPILER
TRANSLATORS
INTERNAL_API
TESTING
PERFORMANCE
VISION
PHILOSOPHY
NON_GOALS
DESIGN_DECISIONS
```

```{toctree}
:maxdepth: 1
:caption: Project

project/support
project/roadmap
MILESTONES
V2_DESIGN
project/changelog
project/contributing
```

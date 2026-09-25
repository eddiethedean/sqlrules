# Errors and Diagnostics

SQLRules separates invalid model declarations, missing columns, unsupported
rules, and backend capability gaps. Compilation never skips a retained rule.

## Public error hierarchy

~~~text
SQLRulesError
├── InvalidModelError
├── MissingColumnError
├── UnsupportedConstraintError
├── CapabilityError
├── TranslatorError
├── InvalidTranslatorError
├── RegistryError
├── ConfigurationError
└── PluginError
~~~

## RuleSchema declaration errors

RuleSchema validates supported declarations when the class is created.
Unsupported scalar/container types, custom validators, serializers, computed
fields, string normalization, arbitrary metadata, duplicate constraints, and
incompatible constraint/type combinations raise TypeError with the original
SQLRules error chained as the cause.

## InvalidModelError

Compiler.compile accepts a RuleSchema class, not an unrestricted Pydantic
BaseModel or an instance. Use from_pydantic() to convert a full model and
inspect its report.

## MissingColumnError

Every RuleSchema field must bind to a database column, including fields with
type-only annotations. Binding order is an explicit column_map entry, then
Field(column=...), then the Python field name. Pydantic aliases do not select
columns implicitly.

## UnsupportedConstraintError

The core or selected plugin has no translator for a retained constraint.
Unlike SQLRules 1.x, warn and ignore policies cannot remove a rule from the
compiled predicate.

## CapabilityError

The backend cannot prove the requested source type, storage representation,
server feature, or safe conversion. This is different from a known row
mismatch:

- Known mismatched value/type: the SQL predicate evaluates to FALSE.
- Missing implementation capability: compilation raises CapabilityError.
- SQL NULL: matches only when the RuleSchema field is nullable.

The error includes backend, field, target type, source type, and reason. Use
the [type support matrix](TYPE_SUPPORT.md) to select supported mappings.

## TranslatorError and InvalidTranslatorError

InvalidTranslatorError is raised when a registry translator is not callable
or cannot accept the translator signature. TranslatorError wraps an exception
raised while building a SQLAlchemy expression or a non-expression return
value.

## ConfigurationError and PluginError

ConfigurationError covers invalid conflict policies, unsupported skipped-rule
policies, and dialect assertions that disagree with the selected provider.
PluginError covers missing or incompatible API v2 declarations, multiple
backend providers, or missing backend hooks.

## Diagnostics

CompiledRules.diagnostics contains compile-scoped structured information.
CompiledRules.explain() includes bindings, conversions, assumptions, and field
predicates. SQLRules does not retain diagnostics across calls on a Compiler.

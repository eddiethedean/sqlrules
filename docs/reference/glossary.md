# Glossary

| Term | Meaning |
|---|---|
| **Application API** | Stable surface for apps: `RuleSchema`, `Field`, `RuleConfig`, `compile`, `where`/`notwhere`, `Compiler`, markers, and exceptions. |
| **Plugin API** | Stable extension surface: `SQLRulesPlugin`, `BackendProvider`, `TranslatorRegistry`, `PLUGIN_API_VERSION`, and translator IR types. |
| **Internal API** | IR builders and helpers that may change without notice. |
| **IR** | Immutable schema, prepared-value, and compiled-result data used between normalization, backend preparation, and translation. |
| **`RuleSchema`** | A Pydantic `BaseModel` whose field declarations are restricted to the SQLRules-compilable subset. It remains usable for normal Pydantic validation and integrations. |
| **`from_pydantic()`** | Converter that creates a RuleSchema-compatible Pydantic model and returns a report of dropped or changed semantics. |
| **`BackendProvider`** | Dialect implementation that reports capabilities and prepares safe SQL expressions from source columns. |
| **`CompiledRules`** | Complete total predicate, per-field result metadata, diagnostics, backend profile, and conversion provenance. |
| **`PatternSpec`** | Structured IR value for `pattern` constraints (flags + text). Use `pattern_text()` in translators. |
| **Marker** | `Annotated` metadata object (`ConstraintMarker`) for dialect operators such as `JsonContains`. |
| **Translator** | Function that turns a `Constraint` + column + context into a SQLAlchemy expression. |
| **Registry** | `TranslatorRegistry` mapping operators (and optionally types) to translators. |
| **Plugin** | Object with `name`, `api_version`, and `register(registry)` that installs translators. |
| **`Compiler`** | Reusable compiler with plugins, conflict policy, and optional backend-name check. |
| **`compile_model` / `bind`** | Two-phase API: normalize a RuleSchema, then bind it to a table or alias. |
| **`on_unsupported`** | Compatibility constructor option. SQLRules 2.0 requires `raise`; retained rules cannot be skipped. |
| **`on_conflict`** | Policy when registering over an existing operator: `raise`, `replace`, or `ignore`. |
| **`notwhere()`** | Returns a one-element predicate list selecting rows that fail the complete compiled rule. |

See also [API](../API.md), [IR_CONTRACT](../IR_CONTRACT.md), and
[INTERNAL_API](../INTERNAL_API.md).

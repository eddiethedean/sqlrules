# Glossary

| Term | Meaning |
|---|---|
| **Application API** | Stable surface for apps: `compile`, `where`/`flatten`, `Compiler`, markers, exceptions. |
| **Plugin API** | Stable extension surface: `SQLRulesPlugin`, `TranslatorRegistry`, `PLUGIN_API_VERSION`, `pattern_text`. |
| **Internal API** | IR builders and helpers that may change without notice. |
| **IR** | Intermediate representation of a model’s fields and constraints (`ModelIR`, `FieldIR`, `Constraint`). |
| **`PatternSpec`** | Structured IR value for `pattern` constraints (flags + text). Use `pattern_text()` in translators. |
| **Marker** | `Annotated` metadata object (`ConstraintMarker`) for dialect operators such as `JsonContains`. |
| **Translator** | Function that turns a `Constraint` + column + context into a SQLAlchemy expression. |
| **Registry** | `TranslatorRegistry` mapping operators (and optionally types) to translators. |
| **Plugin** | Object with `name`, `api_version`, and `register(registry)` that installs translators. |
| **`Compiler`** | Reusable compiler with plugins, conflict policy, cache, and optional `dialect` hint. |
| **`compile_model` / `bind`** | Two-phase API: build IR once, bind to a table (or alias) later. |
| **`on_unsupported`** | Policy for unknown **operators**: `raise`, `warn`, or `ignore`. Does not apply to unsupported types. |
| **`on_conflict`** | Policy when registering over an existing operator: `raise`, `replace`, or `ignore`. |
| **`dialect`** | Optional string hint for translators—not automatic engine detection. |
| **Rules dict** | `dict[str, list[ColumnElement[bool]]]` keyed by Python field names. |

See also [API](../API.md), [IR_CONTRACT](../IR_CONTRACT.md), and
[INTERNAL_API](../INTERNAL_API.md).

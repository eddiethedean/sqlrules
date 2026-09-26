# Public API

SQLRules 2.0 has an application API, a versioned plugin API, and internal
implementation modules. Application and plugin APIs follow semantic
versioning. Internal modules may change without notice.

## Application API

| Symbol | Role |
|---|---|
| RuleSchema | Pydantic v2 BaseModel restricted to SQL-compilable declarations |
| Field | Pydantic Field wrapper with SQLRules-only column binding metadata |
| RuleConfig | SQLRules model options, including explicit allow_empty |
| from_pydantic | Convert an unrestricted Pydantic class and return a loss report |
| Compiler / compile | Normalize a RuleSchema and bind it through one explicit backend |
| CompiledRules | Complete total predicate, field results, diagnostics, and explain plan |
| where / flatten | One-item list containing the complete root predicate |
| notwhere | One-item list containing the root predicate complement |
| CapabilityError | Backend cannot prove or implement a retained rule |
| SQLRulesError hierarchy | Stable public compilation errors |

Example:

~~~python
from sqlalchemy import Column, Integer, MetaData, String, Table

from sqlrules import Compiler, RuleSchema, notwhere, where
from sqlrules_postgresql import PostgresPlugin

users = Table(
    "users",
    MetaData(),
    Column("id", Integer),
    Column("age", Integer),
    Column("name", String),
)


class UserRules(RuleSchema):
    id: int
    age: int | None


compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)
matches = users.select().where(*where(compiled))
failures = users.select().where(*notwhere(compiled))
print("compiled fields:", [field.name for field in compiled.fields])
print("match/failure predicates:", len(where(compiled)), len(notwhere(compiled)))
~~~

Output:

~~~text
compiled fields: ['id', 'age']
match/failure predicates: 1 1
~~~

The module-level compile() has the same explicit provider requirement:

~~~text
sqlrules.compile(model, table, *, plugins, column_map=None) -> CompiledRules
~~~

model must be a RuleSchema class. Direct compilation of an unrestricted
Pydantic BaseModel raises InvalidModelError; call from_pydantic() first.
column_map maps Python field names to SQLAlchemy columns. Field(column=...)
selects a column name without changing Pydantic aliases.

## RuleSchema behavior

RuleSchema is a full Pydantic v2 model. Instances support normal construction,
model_validate(), model_dump(), Pydantic validation errors, and FastAPI route
integration. It also validates declarations during class construction.

Supported declarations include scalar annotations, homogeneous Literal and
Enum domains, nullable fields, supported Pydantic constraints, strict aliases,
and supported metadata in Annotated. Type-only scalar annotations compile a
type predicate. Pydantic defaults and default factories keep their runtime
behavior but never become SQL defaults or bypass column checks.

SQL-only column mapping is written with SQLRules Field:

~~~python
from sqlrules import Field, RuleSchema


class UserRules(RuleSchema):
    display_name: str = Field(column="name")
~~~

An empty RuleSchema is rejected unless it declares
__rule_config__ = RuleConfig(allow_empty=True). An allowed empty schema
compiles to TRUE.

## Pydantic conversion

~~~python
from pydantic import BaseModel, Field

from sqlrules.integrations.pydantic import from_pydantic


class ApiModel(BaseModel):
    age: int = Field(ge=18)


conversion = from_pydantic(
    ApiModel,
    on_incompatible="warn",  # warn, drop, or raise
)
RulesModel = conversion.model
report = conversion.report
print("rules model:", RulesModel.__name__)
print("fields:", list(RulesModel.model_fields))
print("report outcomes:", [(entry.feature, entry.outcome) for entry in report.entries])
~~~

Output:

~~~text
rules model: ApiModelRules
fields: ['age']
report outcomes: [('ge=18', 'preserved'), ('field type and supported constraints', 'preserved')]
~~~

The conversion report records retained rules, descriptive metadata,
unsupported callbacks, dropped fields or constraints, and changed or unknown
semantics. Conversion never runs validators, serializers, or default
factories.

## CompiledRules

CompiledRules is an immutable result containing:

- predicate: the complete SQLAlchemy predicate with total TRUE/FALSE behavior.
- fields: ordered FieldResult entries containing field predicates, bindings,
  logical types, strictness, nullability, coercions, and capabilities.
- diagnostics: compile-scoped structured diagnostics.
- backend, server_version, and assumptions.
- explain(): a structured plan; it does not execute database EXPLAIN.

where(compiled) returns [compiled.predicate]. notwhere(compiled) returns
[~compiled.predicate]. flatten(compiled) remains an alias for where(). Each
helper accepts only a CompiledRules result.

## Compiler

~~~python
from sqlalchemy import Column, Integer, MetaData, Table

from sqlrules import Compiler, RuleSchema
from sqlrules_postgresql import PostgresPlugin

users = Table("users", MetaData(), Column("id", Integer))


class UserRules(RuleSchema):
    id: int


compiler = Compiler(
    plugins=[PostgresPlugin(server_version=(16, 0))],
    registry=None,
    on_conflict="raise",
    dialect=None,
)
schema_ir = compiler.compile_model(UserRules)
compiled = compiler.bind(schema_ir, users, column_map=None)
print("compiled fields:", [field.name for field in compiled.fields])
~~~

Output:

~~~text
compiled fields: ['id']
~~~

Exactly one backend provider must be present when bind() or compile() runs.
Constraint-only plugins may be included with it. on_conflict controls plugin
registration. Unsupported retained operators always raise; warn and ignore
policies are not available because they could omit a declared rule.

compile_model() normalizes the schema without a database backend. bind()
resolves columns and uses a backend provider. The compiler keeps an immutable
registry snapshot and per-call diagnostics, so independent compiles do not
share mutable compilation state.

## Plugin API

| Symbol | Role |
|---|---|
| PLUGIN_API_VERSION | Exact API contract string, currently 2 |
| SQLRulesPlugin | name, api_version, and register(registry) protocol |
| BackendProvider | Adds prepare_value() and capabilities() |
| TranslatorRegistry | Copyable registry for normalized-expression translators |
| PreparedValue | Source, normalized value, validity, null state, and provenance |
| Constraint, PatternSpec, CompilationContext | Translator-facing IR types |
| ConstraintMarker and marker dataclasses | Dialect operator metadata |

The translator's expression argument is the backend-prepared value, not the
raw source column. Backend providers are responsible for safe conversion and
source type evidence. API v1 plugins must be adapted to these requirements.

See [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md) and [IR_CONTRACT](IR_CONTRACT.md).

## Internal API

Implementation modules such as sqlrules.models, sqlrules.backend,
sqlrules.columns, sqlrules.constraints, and private translator factories are
not compatibility surfaces. Import public types from sqlrules instead.

## Exceptions

- InvalidModelError
- MissingColumnError
- UnsupportedConstraintError
- CapabilityError
- TranslatorError / InvalidTranslatorError
- RegistryError
- ConfigurationError
- PluginError
- InternalCompilerError

See [ERRORS](ERRORS.md).

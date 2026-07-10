# SQLRules Compiler Architecture

## Purpose

The SQLRules compiler transforms a constrained Pydantic model into a
dictionary of SQLAlchemy WHERE expressions.

The compiler never connects to a database, executes SQL, or generates
SQL strings. It only produces SQLAlchemy expression objects.

## Pipeline

``` text
Pydantic Model
      │
      ▼
Model Introspection
      │
      ▼
Field Extraction
      │
      ▼
Constraint Extraction
      │
      ▼
Intermediate Representation (IR)
      │
      ▼
Constraint Translators
      │
      ▼
SQLAlchemy Expressions
      │
      ▼
Rule Dictionary
```

## Stage 1 -- Model Introspection

Inputs: - Pydantic BaseModel subclass - SQLAlchemy Table, Alias, ORM
class, or column mapping

Responsibilities: - Validate the input model. - Enumerate model
fields. - Preserve declaration order.

Output: - Iterable of field definitions.

## Stage 2 -- Field Extraction

For each field:

-   Python type
-   Optionality
-   Metadata
-   Field name
-   Alias (optional)

Unsupported field definitions fail fast.

## Stage 3 -- Constraint Extraction

Read only constraints that have deterministic SQL equivalents.

Examples: - gt - ge - lt - le - multiple_of - min_length - max_length -
Literal - Enum

Constraints without SQL equivalents are delegated to the
unsupported-constraint policy.

## Stage 4 -- Intermediate Representation

Each constraint becomes a normalized object.

Example:

``` text
Constraint(
    field="age",
    operator="ge",
    value=18,
)
```

The IR isolates compiler logic from both Pydantic and SQLAlchemy APIs.

## Stage 5 -- Translators

Each constraint is translated independently.

Examples:

-   ge → column \>= value
-   gt → column \> value
-   min_length → func.length(column) \>= value
-   Literal → column.in\_(...)

Every translator returns one SQLAlchemy expression.

## Stage 6 -- Rule Assembly

Expressions are grouped by field.

Example:

``` python
{
    "age": [
        users.c.age >= 18,
        users.c.age <= 65,
    ]
}
```

Ordering is deterministic and follows the source model.

## Error Handling

Modes:

-   raise (default)
-   warn
-   ignore

Errors include:

-   UnsupportedConstraintError
-   MissingColumnError
-   InvalidModelError
-   TranslatorError

## Caching

Future versions may cache compiled metadata using the model type as the
cache key. Translation remains deterministic.

## Extension Points

Future plugin hooks:

-   Register custom translators.
-   Register dialect-specific translators.
-   Override built-in mappings.
-   Add new IR transforms.

## Design Principles

-   Pure function compiler
-   No database dependency
-   Deterministic output
-   SQLAlchemy-first
-   Easy to test
-   Easy to extend
-   Fail fast on unsupported semantics

## Public Contract

``` python
rules = sqlrules.compile(UserFilter, users)
```

Returns:

``` python
dict[str, list]
```

where each value is a list of SQLAlchemy boolean expressions suitable
for passing directly to `.where(*expressions)`.

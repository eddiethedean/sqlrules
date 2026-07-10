from sqlrules.compiler import Compiler, clear_model_cache, compile, flatten, where
from sqlrules.constraints import pattern_text
from sqlrules.errors import (
    ConfigurationError,
    InternalCompilerError,
    InvalidModelError,
    InvalidTranslatorError,
    MissingColumnError,
    PluginError,
    RegistryError,
    SQLRulesError,
    TranslatorError,
    UnsupportedConstraintError,
)
from sqlrules.ir import (
    CompilationContext,
    Constraint,
    Diagnostic,
    FieldDescriptor,
    FieldIR,
    ModelIR,
    PatternSpec,
)
from sqlrules.markers import (
    ArrayContains,
    ArrayOverlap,
    ConstraintMarker,
    FullTextMatch,
    JsonContains,
    JsonHasKey,
    RangeContains,
    RangeOverlap,
)
from sqlrules.plugins import PLUGIN_API_VERSION, SQLRulesPlugin
from sqlrules.translators import SQLRulesWarning, TranslatorRegistry, default_registry

__version__ = "1.0.0"

__all__ = [
    "PLUGIN_API_VERSION",
    "ArrayContains",
    "ArrayOverlap",
    "CompilationContext",
    "Compiler",
    "ConfigurationError",
    "Constraint",
    "ConstraintMarker",
    "Diagnostic",
    "FieldDescriptor",
    "FieldIR",
    "FullTextMatch",
    "InternalCompilerError",
    "InvalidModelError",
    "InvalidTranslatorError",
    "JsonContains",
    "JsonHasKey",
    "MissingColumnError",
    "ModelIR",
    "PatternSpec",
    "PluginError",
    "RangeContains",
    "RangeOverlap",
    "RegistryError",
    "SQLRulesError",
    "SQLRulesPlugin",
    "SQLRulesWarning",
    "TranslatorError",
    "TranslatorRegistry",
    "UnsupportedConstraintError",
    "__version__",
    "clear_model_cache",
    "compile",
    "default_registry",
    "flatten",
    "pattern_text",
    "where",
]

from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_mysql.fulltext import translate_fulltext_match
from sqlrules_mysql.json import translate_json_contains, translate_json_has_key
from sqlrules_mysql.pattern import translate_pattern
from sqlrules_mysql.type_check import translate_type_check

__version__ = "1.0.1"


class MysqlPlugin:
    """Register MySQL / MariaDB constraint translators."""

    name = "mysql"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            translate_pattern,
            on_conflict="replace",
        )
        registry.register_constraint(
            "type_check",
            translate_type_check,
            on_conflict="replace",
        )
        for operator, translator in (
            ("json_contains", translate_json_contains),
            ("json_has_key", translate_json_has_key),
            ("fulltext_match", translate_fulltext_match),
        ):
            registry.register_constraint(operator, translator, on_conflict="replace")


__all__ = [
    "MysqlPlugin",
    "__version__",
    "translate_fulltext_match",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_pattern",
    "translate_type_check",
]

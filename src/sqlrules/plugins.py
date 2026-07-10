from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sqlrules.errors import PluginError
from sqlrules.translators import TranslatorRegistry

PLUGIN_API_VERSION = "1"
"""Version of the translator plugin contract.

API v1 covers:

- ``SQLRulesPlugin`` shape (``name``, ``api_version``, ``register``)
- ``TranslatorRegistry.register_constraint`` / ``register`` / ``copy`` /
  ``operators`` / ``lookup`` / ``translate``
- Translator signature ``(Constraint, ColumnElement, CompilationContext)``
- IR value types for built-in operators, including ``PatternSpec`` for
  ``pattern`` (use ``pattern_text()``; do not assume ``constraint.value``
  is a bare ``str``) and ``TypeSpec`` for ``type_check`` (use ``type_spec()``)
- Stable marker operator names (``json_contains``, ``array_contains``, …)

Bump this string on incompatible changes to any of the above. Package
minor bumps alone do not change ``PLUGIN_API_VERSION``.
"""


@runtime_checkable
class SQLRulesPlugin(Protocol):
    """Explicit extension that registers translators onto a registry."""

    name: str
    api_version: str

    def register(self, registry: TranslatorRegistry) -> None:
        """Register constraint translators on ``registry``."""


def validate_plugin(plugin: Any) -> SQLRulesPlugin:
    """Validate a plugin object against the versioned plugin API."""
    if isinstance(plugin, type):
        raise PluginError(
            message=(
                f"Plugin {plugin!r} is a class; pass an instance "
                f"(e.g. {getattr(plugin, '__name__', 'Plugin')}())."
            ),
            plugin=plugin,
        )

    if not isinstance(plugin, SQLRulesPlugin):
        raise PluginError(
            message=(
                f"Plugin {plugin!r} does not implement SQLRulesPlugin "
                "(requires name, api_version, and register(registry))."
            ),
            plugin=plugin,
        )

    name = getattr(plugin, "name", None)
    if not isinstance(name, str) or not name:
        raise PluginError(
            message=f"Plugin {plugin!r} must declare a non-empty string name.",
            plugin=plugin,
        )

    api_version = getattr(plugin, "api_version", None)
    if api_version != PLUGIN_API_VERSION:
        raise PluginError(
            message=(
                f"Plugin {name!r} declares api_version={api_version!r}, "
                f"but SQLRules plugin API is {PLUGIN_API_VERSION!r}."
            ),
            plugin=plugin,
        )

    register = getattr(plugin, "register", None)
    if not callable(register):
        raise PluginError(
            message=f"Plugin {name!r} must provide a callable register(registry) method.",
            plugin=plugin,
        )

    return plugin

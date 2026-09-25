from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast, runtime_checkable

from sqlrules.errors import PluginError
from sqlrules.translators import TranslatorRegistry

PLUGIN_API_VERSION = "2"
"""Version of the backend preparation and translator plugin contract.

API v2 covers:

- ``SQLRulesPlugin`` shape (``name``, ``api_version``, ``register``)
- optional ``BackendProvider`` shape (``prepare_value`` and ``capabilities``)
- translators consume a normalized prepared-value expression
- explicit selection of exactly one backend provider for table binding
- IR value types for built-in operators, including ``PatternSpec`` for
  ``pattern`` (use ``pattern_text()``; do not assume a bare ``str``)
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


@runtime_checkable
class BackendProvider(Protocol):
    """A dialect provider that prepares source values and reports capabilities."""

    name: str
    api_version: str
    server_version: tuple[int, ...] | None

    def prepare_value(self, column: Any, field: Any, context: Any) -> Any:
        """Return a safe PreparedValue for one source column and logical field."""

    def capabilities(self) -> Mapping[str, Any]:
        """Describe the configured server and semantic capabilities."""


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


def validate_backend(plugin: Any) -> BackendProvider:
    """Validate that a registered plugin supplies SQLRules API v2 backend hooks."""
    validate_plugin(plugin)
    if not callable(getattr(plugin, "prepare_value", None)) or not callable(
        getattr(plugin, "capabilities", None)
    ):
        raise PluginError(
            message=(
                f"Plugin {getattr(plugin, 'name', plugin)!r} does not provide the "
                "API v2 backend hooks prepare_value() and capabilities()."
            ),
            plugin=plugin,
        )
    return cast(BackendProvider, plugin)

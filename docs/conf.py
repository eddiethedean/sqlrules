"""Sphinx configuration for SQLRules."""

from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.application import Sphinx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "SQLRules"
author = "SQLRules Contributors"
release = importlib.metadata.version("sqlrules")
version = ".".join(release.split(".")[:2])
copyright = f"2024–2026, {author}"

myst_substitutions = {
    "release": release,
    "python_requires": "3.10+",
}

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "README.md",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

root_doc = "index"

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "linkify",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 4
myst_linkify_fuzzy_links = False
myst_url_schemes = ("http", "https", "mailto")

html_theme = "furo"
html_title = "SQLRules"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_favicon = "_static/favicon.svg"
html_theme_options = {
    "light_logo": "logo.svg",
    "dark_logo": "logo-dark.svg",
    "source_repository": "https://github.com/eddiethedean/sqlrules",
    "source_branch": "main",
    "source_directory": "docs/",
    "sidebar_hide_name": True,
    "top_of_page_buttons": ["view", "edit"],
    "light_css_variables": {
        "color-brand-primary": "#0f766e",
        "color-brand-content": "#115e59",
        "color-brand-visited": "#0e7490",
        "color-background-primary": "#fafbfc",
        "color-background-secondary": "#f1f5f9",
        "color-background-hover": "#e2e8f0",
        "color-background-border": "#e2e8f0",
        "color-foreground-primary": "#0f172a",
        "color-foreground-secondary": "#475569",
        "color-foreground-muted": "#64748b",
        "color-foreground-border": "#cbd5e1",
        "color-api-background": "#f8fafc",
        "color-api-background-hover": "#f1f5f9",
        "color-api-overall": "#ccfbf1",
        "color-api-keyword": "#0f766e",
        "color-api-name": "#0f172a",
        "color-api-pre-name": "#64748b",
        "font-stack": (
            "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, "
            "'Helvetica Neue', Arial, sans-serif"
        ),
        "font-stack--monospace": (
            "ui-monospace, 'SF Mono', 'Cascadia Code', 'Segoe UI Mono', "
            "Menlo, Consolas, monospace"
        ),
    },
    "dark_css_variables": {
        "color-brand-primary": "#2dd4bf",
        "color-brand-content": "#5eead4",
        "color-brand-visited": "#67e8f9",
        "color-background-primary": "#0b1120",
        "color-background-secondary": "#111827",
        "color-background-hover": "#1e293b",
        "color-background-border": "#334155",
        "color-foreground-primary": "#f1f5f9",
        "color-foreground-secondary": "#94a3b8",
        "color-foreground-muted": "#64748b",
        "color-foreground-border": "#475569",
        "color-api-background": "#0f172a",
        "color-api-background-hover": "#1e293b",
        "color-api-overall": "#134e4a",
        "color-api-keyword": "#2dd4bf",
        "color-api-name": "#f8fafc",
        "color-api-pre-name": "#94a3b8",
    },
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/eddiethedean/sqlrules",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0"
                     viewBox="0 0 16 16" height="1.2em" width="1.2em"
                     xmlns="http://www.w3.org/2000/svg">
                  <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54
                    2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                    0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01
                    1.08.58 1.23.82.72 1.21 1.87.87
                    2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
                    0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12
                    0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2
                    .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08
                    2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65
                    3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0
                    .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z">
                  </path>
                </svg>
            """,
            "class": "",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/sqlrules/",
            "html": '<span class="sr-footer-pypi">PyPI</span>',
            "class": "",
        },
    ],
}

html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")

pygments_style = "sphinx"
pygments_dark_style = "monokai"

autodoc_typehints = "description"
autodoc_member_order = "bysource"
autosummary_generate = True
napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://pydantic.dev/docs/validation/latest", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True


def _apply_myst_substitutions_in_source(
    _app: Sphinx, _docname: str, source: list[str]
) -> None:
    """Expand myst_substitutions before parse (including raw HTML)."""
    text = source[0]
    for key, value in myst_substitutions.items():
        token = f"{{{{ {key} }}}}"
        if token in text:
            text = text.replace(token, value)
    source[0] = text


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect("source-read", _apply_myst_substitutions_in_source)
    return {"version": "1.0", "parallel_read_safe": True}

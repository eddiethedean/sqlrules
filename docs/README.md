# Docs contributor notes

Build:

```bash
pip install -e ".[docs]"
sphinx-build -W -b html docs docs/_build/html
```

Layout:

| Path | Role |
|---|---|
| `guides/` | Tutorials, FAQ, troubleshooting, philosophy |
| `reference/` | Narrative hub, glossary, autodoc |
| `project/` | Changelog, roadmap, contributing (includes from repo root) |
| Root `*.md` | Spec, architecture, and design source pages |

Landing page and branding live in `index.md`, `conf.py`, and `_static/`.

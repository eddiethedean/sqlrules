#!/usr/bin/env python3
"""Assert core/plugin version lockstep and extras pins (CI + local)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = (
    "sqlrules-postgresql",
    "sqlrules-sqlite",
    "sqlrules-mysql",
    "sqlrules-mssql",
)


def init_version(path: Path) -> str:
    text = path.read_text()
    marker = '__version__ = "'
    start = text.index(marker) + len(marker)
    end = text.index('"', start)
    return text[start:end]


def major_line_pin(package: str, version: str) -> str:
    major = int(version.split(".", 1)[0])
    if major == 0:
        minor = int(version.split(".")[1])
        return f"{package}>={major}.{minor},<{major}.{minor + 1}"
    return f"{package}>={major},<{major + 1}"


def main() -> int:
    core_meta = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    core = core_meta["version"]
    assert core == init_version(ROOT / "src/sqlrules/__init__.py"), core
    print(f"core version ok: {core}")

    extras = core_meta.get("optional-dependencies", {})
    for pkg in PLUGINS:
        root = ROOT / "packages" / pkg
        meta = tomllib.loads((root / "pyproject.toml").read_text())["project"]
        version = meta["version"]
        assert version == core, (pkg, version, core)
        init = next((root / "src").rglob("__init__.py"))
        assert version == init_version(init), (pkg, version)
        deps = " ".join(meta["dependencies"])
        expected_core_pin = major_line_pin("sqlrules", core)
        assert expected_core_pin in deps, (pkg, deps, expected_core_pin)
        assert (root / "LICENSE").is_file(), pkg
        assert list((root / "src").rglob("py.typed")), pkg

        extra_key = pkg.removeprefix("sqlrules-")
        extra_deps = " ".join(extras.get(extra_key, []))
        expected_extra = major_line_pin(pkg, core)
        assert expected_extra in extra_deps, (extra_key, extra_deps, expected_extra)
        print(f"{pkg} version/packaging ok: {version}")

    dialects = " ".join(extras.get("dialects", []))
    for pkg in PLUGINS:
        assert major_line_pin(pkg, core) in dialects, (pkg, dialects)

    annotated = " ".join(core_meta.get("dependencies", []))
    assert re.search(r"annotated-types>=0\.6,<1", annotated), annotated
    print("extras + annotated-types pins ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

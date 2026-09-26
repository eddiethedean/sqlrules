"""Execute documented Python examples and verify their captured output."""

from __future__ import annotations

import os
import runpy
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SCRIPTS = (
    "basic_compile.py",
    "select_usage.py",
    "postgresql_pattern.py",
)


@dataclass(frozen=True)
class Fence:
    language: str
    line: int
    content: str


def _read_fences(path: Path) -> list[Fence]:
    lines = path.read_text(encoding="utf-8").splitlines()
    fences: list[Fence] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        marker = line[:3]
        if marker not in {"```", "~~~"}:
            index += 1
            continue

        language = line[3:].strip()
        if language not in {"python", "py", "text"}:
            index += 1
            continue

        start_line = index + 2
        index += 1
        content: list[str] = []
        while index < len(lines) and not lines[index].startswith(marker):
            content.append(lines[index])
            index += 1

        if index == len(lines):
            raise ValueError(f"Unclosed {language} fence at {path}:{start_line - 1}")

        fences.append(Fence(language, start_line, "\n".join(content)))
        index += 1

    return fences


def _markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and ".venv" not in path.parts and "_build" not in path.parts
    )


def _check_markdown_examples(paths: list[Path]) -> tuple[int, int]:
    python_count = 0
    output_count = 0
    failures: list[str] = []

    for path in paths:
        fences = _read_fences(path)
        slug = path.relative_to(ROOT).as_posix().replace("/", "_").replace(".", "_")
        module_name = f"_sqlrules_doc_examples_{slug}"
        module = ModuleType(module_name)
        module.__file__ = str(path)
        sys.modules[module_name] = module
        namespace = module.__dict__

        try:
            for index, fence in enumerate(fences):
                if fence.language not in {"python", "py"}:
                    continue

                python_count += 1
                output = StringIO()
                try:
                    with redirect_stdout(output):
                        exec(
                            compile(fence.content, f"{path}:{fence.line}", "exec"),
                            namespace,
                        )
                except Exception as error:  # noqa: BLE001 - report the failing example itself
                    failures.append(
                        f"{path.relative_to(ROOT)}:{fence.line}: {type(error).__name__}: {error}"
                    )
                    continue

                actual = output.getvalue().rstrip("\n")
                if not actual:
                    continue

                output_count += 1
                expected_fence = fences[index + 1] if index + 1 < len(fences) else None
                if expected_fence is None or expected_fence.language != "text":
                    failures.append(
                        f"{path.relative_to(ROOT)}:{fence.line}: printed output "
                        "must be followed by a fenced text output block"
                    )
                    continue

                expected = expected_fence.content.rstrip("\n")
                if actual != expected:
                    failures.append(
                        f"{path.relative_to(ROOT)}:{fence.line}: printed output "
                        "does not match the following text block"
                    )
        finally:
            sys.modules.pop(module_name, None)

    if failures:
        raise SystemExit("Documentation examples failed:\n- " + "\n- ".join(failures))

    return python_count, output_count


def _example_output_blocks(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    expected: dict[str, str] = {}
    name: str | None = None
    capture = False
    content: list[str] = []

    for line in lines:
        if line.startswith("### `"):
            name = line.removeprefix("### `").removesuffix("`")
            content = []
            continue
        if name is None:
            continue
        if line == "```text":
            capture = True
            content = []
            continue
        if capture and line == "```":
            expected[name] = "\n".join(content)
            capture = False
            name = None
            continue
        if capture:
            content.append(line)

    return expected


def _check_example_scripts() -> int:
    output_file = ROOT / "examples" / "README.md"
    expected = _example_output_blocks(output_file)
    failures: list[str] = []

    for script in EXAMPLE_SCRIPTS:
        output = StringIO()
        script_path = ROOT / "examples" / script
        try:
            with redirect_stdout(output):
                runpy.run_path(str(script_path), run_name="__main__")
        except Exception as error:  # noqa: BLE001 - report the failing example itself
            failures.append(f"{script}: {type(error).__name__}: {error}")
            continue

        actual = output.getvalue().rstrip("\n")
        if actual != expected.get(script, ""):
            failures.append(f"{script}: stdout does not match {output_file.relative_to(ROOT)}")

    if failures:
        raise SystemExit("Runnable example scripts failed:\n- " + "\n- ".join(failures))

    return len(EXAMPLE_SCRIPTS)


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "src"))
    for package in (
        "sqlrules-postgresql",
        "sqlrules-sqlite",
        "sqlrules-mysql",
        "sqlrules-mssql",
    ):
        sys.path.insert(0, str(ROOT / "packages" / package / "src"))

    python_count, output_count = _check_markdown_examples(_markdown_files())
    script_count = _check_example_scripts()
    print(
        f"Verified {python_count} Markdown Python examples and {script_count} runnable scripts; "
        f"matched {output_count} Markdown output blocks and all script transcripts."
    )


if __name__ == "__main__":
    main()

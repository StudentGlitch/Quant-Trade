"""Fail CI if crawler_v2 third-party imports drift from requirements.txt."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = ROOT / "requirements.txt"
SKIP_PARTS = {"tests", "__pycache__"}

# Import module -> PyPI package mapping for common mismatches.
MODULE_TO_PACKAGE = {
    "dotenv": "python-dotenv",
    "fake_useragent": "fake-useragent",
}


def parse_requirements(path: Path) -> set[str]:
    packages: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        line = line.split(";", 1)[0].strip()
        name = re.split(r"[<>=!\[]", line, maxsplit=1)[0].strip().lower()
        if name:
            packages.add(name)
    return packages


def iter_python_files(root: Path):
    for file_path in root.rglob("*.py"):
        if any(part in SKIP_PARTS for part in file_path.parts):
            continue
        if file_path.name == Path(__file__).name:
            continue
        yield file_path


def imported_top_level_modules(root: Path) -> set[str]:
    modules: set[str] = set()
    for file_path in iter_python_files(root):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom):
                # Relative imports are local by definition.
                if node.level and node.level > 0:
                    continue
                if node.module:
                    modules.add(node.module.split(".", 1)[0])
    return modules


def normalize_dependency_name(module: str) -> str:
    return MODULE_TO_PACKAGE.get(module, module).lower().replace("_", "-")


def main() -> int:
    if not REQUIREMENTS_FILE.exists():
        print(f"ERROR: requirements file not found: {REQUIREMENTS_FILE}")
        return 1

    stdlib = set(sys.stdlib_module_names)
    local_top_level = {"crawler_v2"}

    imported = imported_top_level_modules(ROOT)
    third_party = {
        normalize_dependency_name(module)
        for module in imported
        if module not in stdlib and module not in local_top_level
    }
    declared = parse_requirements(REQUIREMENTS_FILE)

    missing = sorted(third_party - declared)
    extra = sorted(declared - third_party)

    print("[crawler_v2 requirements drift check]")
    print(f"- Imported third-party packages: {len(third_party)}")
    print(f"- Declared packages: {len(declared)}")

    if missing:
        print("\nERROR: Missing dependencies in crawler_v2/requirements.txt:")
        for package in missing:
            print(f"  - {package}")

    if extra:
        print("\nERROR: Declared but not directly imported in crawler_v2 runtime files:")
        for package in extra:
            print(f"  - {package}")

    if missing or extra:
        print("\nFAIL: requirements drift detected.")
        return 1

    print("\nPASS: crawler_v2 requirements match imported third-party modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

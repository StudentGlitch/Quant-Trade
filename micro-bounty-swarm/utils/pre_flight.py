import ast
import os
import sys
import json
from pathlib import Path

def analyze_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        return json.dumps({"error": f"File {file_path} not found"}, indent=2)

    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    # Type Hint Analysis
    total_funcs = 0
    funcs_with_hints = 0
    missing_hints = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total_funcs += 1
            has_hints = node.returns is not None
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != 'self':
                    has_hints = False
            
            if has_hints:
                funcs_with_hints += 1
            else:
                missing_hints.append(node.name)

    coverage = (funcs_with_hints / total_funcs * 100) if total_funcs > 0 else 100

    # Dependency Extraction
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                deps.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module)

    test_file_path = Path("tests") / f"test_{path.name}"
    
    output = {
        "target_file": str(path),
        "file_exists": True,
        "test_file_exists": test_file_path.exists(),
        "test_file_path": str(test_file_path),
        "type_hint_coverage_percent": round(coverage, 2),
        "missing_hints": missing_hints,
        "dependencies": sorted(list(deps))
    }
    return json.dumps(output, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No file provided"}, indent=2))
        sys.exit(1)
    print(analyze_file(sys.argv[1]))

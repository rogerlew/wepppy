#!/usr/bin/env python3
"""
Validate that all sys.modules stubs in tests cover the full public API.

Usage:
    python tools/check_stubs.py
    
Exit codes:
    0 - All stubs are complete
    1 - Found incomplete stubs

This tool helps prevent import errors caused by incomplete module stubs
that are registered in sys.modules during test collection.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


def _const_str(node: ast.AST) -> Optional[str]:
    """Return the string value from an AST Constant or Str node."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def get_public_api(module_path: Path) -> Set[str]:
    """Extract __all__ exports from a module's __init__.py."""
    init_file = module_path / "__init__.py"
    if not init_file.exists():
        return set()
    
    tree = ast.parse(init_file.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(
                    node.value, (ast.List, ast.Tuple)
                ):
                    values = set()
                    for elt in node.value.elts:
                        constant = _const_str(elt)
                        if constant is not None:
                            values.add(constant)
                    if values:
                        return values
    return set()


def find_stub_assignments(file_path: Path) -> List[Tuple[str, Set[str], int]]:
    """
    Find sys.modules stub assignments and extract assigned attributes.
    
    Returns:
        List of (module_name, {attribute_names}, line_number) tuples
    """
    stubs = []
    content = file_path.read_text()
    tree = ast.parse(content)
    
    # Track current stub being built
    current_stub: Dict[str, Set[str]] = {}
    
    for node in ast.walk(tree):
        # Look for stub = types.ModuleType("module.name")
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Call):
                        if (
                            isinstance(node.value.func, ast.Attribute)
                            and node.value.func.attr == "ModuleType"
                            and node.value.args
                        ):
                            module_name = _const_str(node.value.args[0])
                            if module_name is not None:
                                current_stub[target.id] = set()
        
        # Look for stub.attribute = value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name):
                        stub_name = target.value.id
                        if stub_name in current_stub:
                            current_stub[stub_name].add(target.attr)
        
        # Look for sys.modules["module.name"] = stub
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if (
                        isinstance(target.value, ast.Attribute)
                        and target.value.attr == "modules"
                        and isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "sys"
                    ):
                        module_name = None
                        if hasattr(target, "slice"):
                            module_name = _const_str(target.slice)
                        elif (
                            hasattr(target, "index")
                            and target.index is not None  # type: ignore[attr-defined]
                        ):
                            module_name = _const_str(target.index)  # type: ignore[attr-defined]
                        if isinstance(node.value, ast.Name):
                            stub_name = node.value.id
                            if module_name and stub_name in current_stub:
                                stubs.append((
                                    module_name,
                                    current_stub[stub_name],
                                        node.lineno
                                    ))
    
    return stubs


def check_stub_completeness() -> bool:
    """
    Check all test files for incomplete sys.modules stubs.
    
    Returns:
        True if all stubs are complete, False otherwise
    """
    # Known modules to check
    modules_to_check = {
        "wepppy.all_your_base": REPO_ROOT / "wepppy" / "all_your_base",
    }
    
    # Get expected public APIs
    expected_apis: Dict[str, Set[str]] = {}
    for module_name, module_path in modules_to_check.items():
        api = get_public_api(module_path)
        if api:
            expected_apis[module_name] = api
    
    # Find all stub assignments in test files
    all_ok = True
    test_files = list((REPO_ROOT / "tests").rglob("*.py"))
    test_files.extend((REPO_ROOT / "wepppy").rglob("*.py"))
    
    for test_file in test_files:
        try:
            stubs = find_stub_assignments(test_file)
        except SyntaxError:
            continue  # Skip files with syntax errors
        
        for module_name, stub_attrs, line_no in stubs:
            if module_name in expected_apis:
                expected = expected_apis[module_name]
                missing = expected - stub_attrs
                
                if missing:
                    all_ok = False
                    rel_path = test_file.relative_to(REPO_ROOT)
                    print(f"\n❌ Incomplete stub in {rel_path}:{line_no}")
                    print(f"   Module: {module_name}")
                    print(f"   Missing: {', '.join(sorted(missing))}")
                    print(f"   Has: {', '.join(sorted(stub_attrs)) if stub_attrs else '(none)'}")
    
    return all_ok


def main() -> int:
    """Run stub completeness checks."""
    print("🔍 Checking sys.modules stubs for completeness...")
    
    if check_stub_completeness():
        print("\n✅ All stubs are complete!")
        return 0
    else:
        print("\n" + "="*60)
        print("⚠️  Found incomplete stubs!")
        print("="*60)
        print("\nTo fix:")
        print("1. Check the module's __all__ exports")
        print("2. Add missing functions/classes to the stub")
        print("3. Consider extracting shared stubs to tests/conftest.py")
        print("\nSee tests/AGENTS.md for stub management guidance.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

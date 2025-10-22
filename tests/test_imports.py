import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def base_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "wepppy")


def test_imports_in_directory(base_path: str):
    print(f"Testing imports in: {base_path}")
    original_sys_path = sys.path[:]  # Save original path
    # Add the base_path to sys.path so modules can be imported
    sys.path.insert(0, base_path)
    package_name = Path(base_path).name

    success_count = 0
    failure_count = 0

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # Construct the module name
                # Relative path from base_path to current file's directory
                relative_dir = os.path.relpath(root, base_path)
                # Remove .py extension
                module_base = file[:-3]

                if relative_dir == '.':
                    if module_base == "__init__":
                        module_name = package_name
                    else:
                        module_name = f"{package_name}.{module_base}"
                else:
                    module_name = f"{package_name}.{relative_dir.replace(os.sep, '.')}.{module_base}"

                print(f"  Attempting to import: {module_name}...")
                try:
                    # Try to import the module
                    # reload(module) if you want to ensure it's re-imported
                    importlib.import_module(module_name)
                    print(f"    SUCCESS: {module_name}")
                    success_count += 1
                except (ImportError, SyntaxError, Exception) as e:
                    print(f"    FAILURE: {module_name} - {type(e).__name__}: {e}")
                    failure_count += 1
    
    sys.path = original_sys_path # Restore original path
    print(f"\n--- Import Test Results ---")
    print(f"Total files checked: {success_count + failure_count}")
    print(f"Successfully imported: {success_count}")
    print(f"Failed to import: {failure_count}")

if __name__ == "__main__":
    import os
    target_directory = "/workdir/wepppy/wepppy"
    if not os.path.isdir(target_directory):
        print(f"Error: Directory not found - {target_directory}")
        sys.exit(1)
    
    test_imports_in_directory(target_directory)

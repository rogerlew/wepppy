"""Inventory WEPPpy module imports in a disposable development checkout."""

import os
from importlib import import_module
from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1] / "wepppy"
    # These developer scripts write management exports at import time.
    excluded = {package / "wepp/management" / name for name in ("scripts", "data")}
    checked = 0
    failures = 0
    for root, directories, files in os.walk(package):
        directory = Path(root)
        directories[:] = sorted(name for name in directories if directory / name not in excluded)
        for filename in sorted(files):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            relative = (directory / filename).relative_to(package.parent).with_suffix("")
            module = ".".join(relative.parts)
            checked += 1
            try:
                import_module(module)
            except (Exception, SystemExit) as exc:  # Record import-time errors and exits per module.
                print(f"FAIL {module}: {type(exc).__name__}: {exc}", flush=True)
                failures += 1

    print(f"Import diagnostic: {checked} checked, {failures} failed.")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())

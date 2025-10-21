"""Compose controllers.js from controllers_js templates.

See README.md in this package for controller architecture details.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys
from typing import Final, List

MODULE_DIR: Final[Path] = Path(__file__).resolve().parent
ROOT: Final[Path] = MODULE_DIR.parent

project_root = ROOT.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jinja2 import Environment, FileSystemLoader

_builder_spec = importlib.util.spec_from_file_location(
    "unitizer_map_builder", MODULE_DIR / "unitizer_map_builder.py"
)
if _builder_spec is None or _builder_spec.loader is None:  # pragma: no cover - defensive
    raise RuntimeError("Unable to import unitizer_map_builder")
_builder_module = importlib.util.module_from_spec(_builder_spec)
sys.modules[_builder_spec.name] = _builder_module
_builder_spec.loader.exec_module(_builder_module)
DEFAULT_UNITIZER_OUTPUT: Final[Path] = _builder_module.DEFAULT_OUTPUT_PATH
write_unitizer_module = _builder_module.write_unitizer_module

TEMPLATES_DIR: Final[Path] = MODULE_DIR / "templates"
OUTPUT_PATH: Final[Path] = ROOT / "static" / "js" / "controllers.js"
PRIORITY_MODULES: Final[List[str]] = [
    "utils.js",
    "modal.js",
    "unitizer_client.js",
    "ws_client.js",
    "status_stream.js",
    "control_base.js",
    "project.js",
]


def _collect_controller_modules() -> List[str]:
    """
    Discover controller source modules (.js files) and return an ordered list.

    Priority modules are emitted first to preserve dependencies (utilities,
    control base, project). Remaining modules are appended alphabetically.
    """
    module_names = sorted(path.name for path in MODULE_DIR.glob("*.js"))

    ordered: List[str] = []
    for name in PRIORITY_MODULES:
        if name in module_names:
            ordered.append(name)
            module_names.remove(name)

    ordered.extend(module_names)
    return ordered


def render_controllers() -> str:
    search_paths = [str(TEMPLATES_DIR), str(MODULE_DIR)]
    env = Environment(
        loader=FileSystemLoader(search_paths),
        autoescape=False,
        variable_start_string="[[",
        variable_end_string="]]",
    )
    template = env.get_template("controllers.js.j2")
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    modules = _collect_controller_modules()
    return template.render(build_date=build_date, modules=modules)


def write_output(contents: str, *, output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(contents, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render controllers.js from controllers_js templates",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Override output path (defaults to static/js/controllers.js)",
    )
    parser.add_argument(
        "--unitizer-output",
        type=Path,
        default=DEFAULT_UNITIZER_OUTPUT,
        help=(
            "Override output path for the generated unitizer_map.js "
            "(defaults to static/js/unitizer_map.js)"
        ),
    )
    args = parser.parse_args()

    contents = render_controllers()
    write_output(contents, output_path=args.output)
    write_unitizer_module(output_path=args.unitizer_output)


if __name__ == "__main__":
    main()

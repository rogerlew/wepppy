"""Compose controllers.js from controllers_js templates.

See README.md in this package for controller architecture details.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys
from typing import Final, List, Set

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
GL_OUTPUT_PATH: Final[Path] = ROOT / "static" / "js" / "controllers-gl.js"
STATUS_STREAM_SOURCE: Final[Path] = MODULE_DIR / "status_stream.js"
STATUS_STREAM_OUTPUT: Final[Path] = ROOT / "static" / "js" / "status_stream.js"
PRIORITY_MODULES: Final[List[str]] = [
    "dom.js",
    "events.js",
    "forms.js",
    "http.js",
    "recorder_interceptor.js",
    "utils.js",
    "modal.js",
    "unitizer_client.js",
    "status_stream.js",
    "control_base.js",
    "bootstrap.js",
    "project.js",
]
GL_PRIORITY_MODULES: Final[List[str]] = list(PRIORITY_MODULES)
GL_EXCLUDED_MODULES: Final[Set[str]] = {
    "map.js",
    "subcatchment_delineation.js",
    "channel_delineation.js",
    "outlet.js",
    "landuse_modify.js",
    "rangeland_cover_modify.js",
    "baer.js",
}


def _collect_controller_modules() -> List[str]:
    """
    Discover controller source modules (.js files) and return an ordered list.

    Priority modules are emitted first to preserve dependencies (utilities,
    control base, project). Remaining modules are appended alphabetically.
    """
    module_names = sorted(
        path.name for path in MODULE_DIR.glob("*.js") if not path.name.endswith("_gl.js")
    )

    ordered: List[str] = []
    for name in PRIORITY_MODULES:
        if name in module_names:
            ordered.append(name)
            module_names.remove(name)

    ordered.extend(module_names)
    return ordered


def _collect_gl_controller_modules() -> List[str]:
    """
    Discover GL controller source modules and return an ordered list.

    GL bundles include helper modules, non-Leaflet controllers, plus *_gl.js stubs.
    """
    module_names = sorted(
        path.name
        for path in MODULE_DIR.glob("*.js")
        if not path.name.endswith("_gl.js")
        and path.name not in GL_EXCLUDED_MODULES
    )

    ordered: List[str] = []
    for name in GL_PRIORITY_MODULES:
        if name in module_names:
            ordered.append(name)
            module_names.remove(name)

    ordered.extend(module_names)
    ordered.extend(sorted(path.name for path in MODULE_DIR.glob("*_gl.js")))
    return ordered


def render_controllers(modules: List[str], *, bundle_name: str) -> str:
    search_paths = [str(TEMPLATES_DIR), str(MODULE_DIR)]
    env = Environment(
        loader=FileSystemLoader(search_paths),
        autoescape=False,
        variable_start_string="[[",
        variable_end_string="]]",
    )
    template = env.get_template("controllers.js.j2")
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return template.render(
        build_date=build_date,
        modules=modules,
        bundle_name=bundle_name,
    )


def write_output(contents: str, *, output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(contents, encoding="utf-8")


def render_status_stream_bundle() -> str:
    source = STATUS_STREAM_SOURCE.read_text(encoding="utf-8")
    header = (
        "/* ----------------------------------------------------------------------------\n"
        " * StatusStream standalone bundle\n"
        " * NOTE: Generated via build_controllers_js.py from\n"
        f" *       {STATUS_STREAM_SOURCE.relative_to(project_root)}\n"
        " * ----------------------------------------------------------------------------\n"
        " */\n"
    )
    return header + source


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
        "--gl-output",
        type=Path,
        default=GL_OUTPUT_PATH,
        help="Override output path (defaults to static/js/controllers-gl.js)",
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
    parser.add_argument(
        "--status-stream-output",
        type=Path,
        default=STATUS_STREAM_OUTPUT,
        help=(
            "Override output path for the standalone StatusStream bundle "
            "(defaults to static/js/status_stream.js)"
        ),
    )
    args = parser.parse_args()

    contents = render_controllers(
        _collect_controller_modules(),
        bundle_name="controllers.js",
    )
    write_output(contents, output_path=args.output)
    gl_contents = render_controllers(
        _collect_gl_controller_modules(),
        bundle_name="controllers-gl.js",
    )
    write_output(gl_contents, output_path=args.gl_output)
    status_stream_bundle = render_status_stream_bundle()
    write_output(status_stream_bundle, output_path=args.status_stream_output)
    write_unitizer_module(output_path=args.unitizer_output)


if __name__ == "__main__":
    main()

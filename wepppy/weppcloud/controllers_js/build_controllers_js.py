"""Compose controllers.js from controllers_js templates.

See README.md in this package for controller architecture details.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader


MODULE_DIR: Final[Path] = Path(__file__).resolve().parent
ROOT: Final[Path] = MODULE_DIR.parent
TEMPLATES_DIR: Final[Path] = MODULE_DIR / "templates"
OUTPUT_PATH: Final[Path] = ROOT / "static" / "js" / "controllers.js"


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
    return template.render(build_date=build_date)


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
    args = parser.parse_args()

    contents = render_controllers()
    write_output(contents, output_path=args.output)


if __name__ == "__main__":
    main()

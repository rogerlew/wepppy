#!/usr/bin/env python3
"""Convert VS Code themes to WEPPcloud CSS bundles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - CLI guard
        raise SystemExit(f"[error] JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI guard
        raise SystemExit(f"[error] Failed to parse JSON {path}: {exc}") from exc


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class RGBA:
    r: int
    g: int
    b: int
    a: float

    def clamp(self) -> "RGBA":
        return RGBA(
            min(255, max(0, int(round(self.r)))),
            min(255, max(0, int(round(self.g)))),
            min(255, max(0, int(round(self.b)))),
            min(1.0, max(0.0, self.a)),
        )

    def to_hex(self, include_alpha: bool = False) -> str:
        clamped = self.clamp()
        if include_alpha:
            alpha = int(round(clamped.a * 255))
            return f"#{clamped.r:02X}{clamped.g:02X}{clamped.b:02X}{alpha:02X}"
        return f"#{clamped.r:02X}{clamped.g:02X}{clamped.b:02X}"

    def to_rgba_string(self) -> str:
        clamped = self.clamp()
        return f"rgba({clamped.r}, {clamped.g}, {clamped.b}, {clamped.a:.3f})"


def parse_color(value: str) -> Optional[RGBA]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.startswith("#"):
        hex_digits = value[1:]
        if len(hex_digits) == 3:
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16)
            b = int(hex_digits[2] * 2, 16)
            return RGBA(r, g, b, 1.0)
        if len(hex_digits) == 4:
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16)
            b = int(hex_digits[2] * 2, 16)
            a = int(hex_digits[3] * 2, 16) / 255.0
            return RGBA(r, g, b, a)
        if len(hex_digits) == 6:
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
            return RGBA(r, g, b, 1.0)
        if len(hex_digits) == 8:
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
            a = int(hex_digits[6:8], 16) / 255.0
            return RGBA(r, g, b, a)
        return None
    if value.startswith("rgba"):
        try:
            parts = value[value.index("(") + 1:value.rindex(")")].split(",")
            r, g, b = [int(float(p)) for p in parts[:3]]
            a = float(parts[3])
            return RGBA(r, g, b, a)
        except (ValueError, IndexError):
            return None
    if value.startswith("rgb"):
        try:
            parts = value[value.index("(") + 1:value.rindex(")")].split(",")
            r, g, b = [int(float(p)) for p in parts[:3]]
            return RGBA(r, g, b, 1.0)
        except (ValueError, IndexError):
            return None
    return None


def mix(color: RGBA, other: RGBA, ratio: float) -> RGBA:
    ratio = max(0.0, min(1.0, ratio))
    inv = 1.0 - ratio
    return RGBA(
        r=color.r * inv + other.r * ratio,
        g=color.g * inv + other.g * ratio,
        b=color.b * inv + other.b * ratio,
        a=color.a * inv + other.a * ratio,
    )


def adjust_alpha(color: RGBA, alpha: float) -> RGBA:
    alpha = max(0.0, min(1.0, alpha))
    return RGBA(color.r, color.g, color.b, alpha)


def relative_luminance(color: RGBA) -> float:
    clamped = color.clamp()

    def channel(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r = channel(clamped.r)
    g = channel(clamped.g)
    b = channel(clamped.b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1: RGBA, c2: RGBA) -> float:
    l1 = relative_luminance(c1)
    l2 = relative_luminance(c2)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


CONTRAST_CHECKS: List[Tuple[str, str, str, float]] = [
    ("Text vs Surface", "--wc-color-text", "--wc-color-surface", 4.5),
    ("Text vs Surface Alt", "--wc-color-text", "--wc-color-surface-alt", 4.5),
    ("Text vs Page", "--wc-color-text", "--wc-color-page", 4.5),
    ("Muted Text vs Surface", "--wc-color-text-muted", "--wc-color-surface", 3.0),
    ("Link vs Surface", "--wc-color-link", "--wc-color-surface", 4.5),
    ("Link vs Surface Alt", "--wc-color-link", "--wc-color-surface-alt", 4.5),
]


class ThemeMapping:
    def __init__(self, mapping_path: Path) -> None:
        self.mapping_path = mapping_path
        self.mapping = load_json(mapping_path)
        self.variables: Dict[str, Any] = self.mapping.get("variables", {})
        self.themes: Dict[str, Any] = self.mapping.get("themes", {})
        self.meta: Dict[str, Any] = self.mapping.get("meta", {})

    def resolve_defaults(self, key: str, default: Optional[str] = None) -> str:
        defaults = self.meta.get("defaults", {})
        return str(defaults.get(key, default or ""))


def resolve_token_value(theme_colors: Dict[str, str], candidate: Any) -> Optional[str]:
    if isinstance(candidate, str):
        return theme_colors.get(candidate)
    if not isinstance(candidate, dict):
        return None
    if "literal" in candidate:
        return candidate["literal"]
    token = candidate.get("token")
    if not token:
        return None
    raw = theme_colors.get(token)
    if not raw:
        return None
    color = parse_color(raw)
    if color is None:
        return raw
    working = color
    if "lighten" in candidate:
        working = mix(working, RGBA(255, 255, 255, working.a), float(candidate["lighten"]))
    if "darken" in candidate:
        working = mix(working, RGBA(0, 0, 0, working.a), float(candidate["darken"]))
    if "alpha" in candidate:
        working = adjust_alpha(working, float(candidate["alpha"]))
        return working.to_rgba_string()
    return working.to_hex(include_alpha=working.a < 1.0)


def build_variable_map(
    mapping: ThemeMapping,
    theme_slug: str,
    theme_colors: Dict[str, str],
    theme_overrides: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, str], List[str]]:
    assignments: Dict[str, str] = {}
    missing: List[str] = []
    overrides = theme_overrides or {}

    for var_name, spec in mapping.variables.items():
        value = overrides.get(var_name)
        if value is None:
            per_var_overrides = spec.get("overrides", {})
            value = per_var_overrides.get(theme_slug)
        if value is None:
            for candidate in spec.get("tokens", []):
                resolved = resolve_token_value(theme_colors, candidate)
                if resolved:
                    value = resolved
                    break
        if value is None:
            value = spec.get("fallback")
            missing.append(var_name)
        if value is None:
            continue
        assignments[var_name] = str(value)

    return assignments, missing


def format_css_block(theme_slug: str, assignments: Dict[str, str]) -> str:
    lines = [f":root[data-theme=\"{theme_slug}\"] {{"]
    for key in sorted(assignments.keys()):
        lines.append(f"  {key}: {assignments[key]};")
    lines.append("}")
    return "\n".join(lines)


def evaluate_contrast(assignments: Dict[str, str]) -> List[Tuple[str, float, float]]:
    failures: List[Tuple[str, float, float]] = []
    for description, fg_var, bg_var, required in CONTRAST_CHECKS:
        fg_val = assignments.get(fg_var)
        bg_val = assignments.get(bg_var)
        if not fg_val or not bg_val:
            continue
        fg = parse_color(fg_val)
        bg = parse_color(bg_val)
        if not fg or not bg:
            continue
        ratio = contrast_ratio(fg, bg)
        if ratio < required:
            failures.append((description, ratio, required))
    return failures


def apply_flat_card_styles(theme_slug: str) -> str:
    return (
        f":root[data-theme=\"{theme_slug}\"] .wc-card, "
        f":root[data-theme=\"{theme_slug}\"] .wc-control, "
        f":root[data-theme=\"{theme_slug}\"] .wc-panel {{\n"
        "  border-color: transparent;\n"
        "  box-shadow: none;\n"
        "}\n"
    )


def apply_no_shadow(theme_slug: str) -> str:
    return (
        f":root[data-theme=\"{theme_slug}\"] .wc-card, "
        f":root[data-theme=\"{theme_slug}\"] .wc-control, "
        f":root[data-theme=\"{theme_slug}\"] .wc-panel {{\n"
        "  box-shadow: none;\n"
        "}\n"
    )


def build_theme_css(
    args: argparse.Namespace,
    mapping: ThemeMapping,
    theme_slug: str,
    theme_cfg: Dict[str, Any],
) -> Tuple[str, List[str], List[Tuple[str, float, float]]]:
    themes_dir = Path(args.themes_dir or mapping.resolve_defaults("themes_dir"))
    source = theme_cfg.get("source")
    if not source:
        raise SystemExit(f"[error] Theme '{theme_slug}' is missing a 'source' field.")
    theme_path = themes_dir / source
    data = load_json(theme_path)
    theme_colors = data.get("colors", {})

    assignments, missing = build_variable_map(mapping, theme_slug, theme_colors, theme_cfg.get("overrides"))

    css_parts = [
        f"/* Generated from {source} on {datetime.now(timezone.utc).isoformat()} */",
        format_css_block(theme_slug, assignments),
    ]

    options = theme_cfg.get("options", {})
    if options.get("flat_cards"):
        css_parts.append(apply_flat_card_styles(theme_slug))
    elif options.get("suppress_shadows"):
        css_parts.append(apply_no_shadow(theme_slug))

    for snippet in theme_cfg.get("extra_css", []):
        css_parts.append(snippet)

    css_text = "\n".join(css_parts).rstrip() + "\n"
    contrast_failures = evaluate_contrast(assignments)
    return css_text, missing, contrast_failures


def reset_mapping(mapping_path: Path, defaults_path: Path) -> None:
    defaults = load_json(defaults_path)
    mapping_path.write_text(json.dumps(defaults, indent=2) + "\n", encoding="utf-8")
    print(f"[info] Reset {mapping_path} from {defaults_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert VS Code themes to WEPPcloud CSS.")
    parser.add_argument("--mapping", type=Path, help="Path to theme-mapping.json")
    parser.add_argument("--mapping-defaults", type=Path, help="Path to defaults mapping JSON")
    parser.add_argument("--themes-dir", type=Path, help="Directory containing theme JSON files")
    parser.add_argument("--output-dir", type=Path, help="Directory to write generated CSS")
    parser.add_argument("--combined-file", type=str, help="Filename for combined CSS bundle")
    parser.add_argument("--theme", action="append", dest="themes", help="Convert only the specified theme slug(s)")
    parser.add_argument("--validate-only", action="store_true", help="Validate without writing CSS files")
    parser.add_argument("--report", type=Path, help="Write JSON contrast report to this path")
    parser.add_argument("--md-report", type=Path, help="Write Markdown contrast summary to this path")
    parser.add_argument("--reset-mapping", action="store_true", help="Reset editable mapping to defaults")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    script_dir = Path(__file__).resolve()
    project_root = script_dir.parents[2]

    mapping_path = args.mapping or (project_root / "themes" / "theme-mapping.json")
    defaults_path = args.mapping_defaults or (project_root / "themes" / "theme-mapping.defaults.json")

    if args.reset_mapping:
        reset_mapping(Path(mapping_path), Path(defaults_path))
        return

    mapping = ThemeMapping(Path(mapping_path))

    themes_dir = Path(args.themes_dir or mapping.resolve_defaults("themes_dir") or (project_root / "themes"))
    output_dir = Path(args.output_dir or mapping.resolve_defaults("output_dir") or (project_root / "static/css/themes"))
    combined_filename = args.combined_file or mapping.resolve_defaults("combined_file") or "all-themes.css"

    slugs = list(mapping.themes.keys())
    if args.themes:
        requested = set(args.themes)
        unknown = requested.difference(slugs)
        if unknown:
            raise SystemExit(f"[error] Unknown theme(s) requested: {', '.join(sorted(unknown))}")
        slugs = [slug for slug in slugs if slug in requested]

    if not slugs:
        print("[warn] No themes defined in mapping. Nothing to do.")
        return

    combined_css: List[str] = []
    missing_map: Dict[str, List[str]] = {}
    contrast_map: Dict[str, List[Tuple[str, float, float]]] = {}

    for slug in slugs:
        cfg = mapping.themes.get(slug, {})
        if cfg.get("disabled"):
            continue
        css_text, missing, contrast_failures = build_theme_css(args, mapping, slug, cfg)
        missing_map[slug] = missing
        contrast_map[slug] = contrast_failures
        combined_css.append(css_text)

        if args.validate_only:
            continue

        ensure_dir(output_dir)
        out_path = output_dir / f"{slug}.css"
        out_path.write_text(css_text, encoding="utf-8")
        print(f"[info] wrote {out_path}")

    if not args.validate_only:
        ensure_dir(output_dir)
        combined_path = output_dir / combined_filename
        combined_path.write_text("\n".join(combined_css).rstrip() + "\n", encoding="utf-8")
        print(f"[info] wrote combined bundle {combined_path}")

    print("\n=== Validation Summary ===")
    for slug in slugs:
        missing = missing_map.get(slug, [])
        if missing:
            print(f"[warn] {slug}: {len(missing)} variables used fallback values")
            for name in missing:
                print(f"   - {name}")
        else:
            print(f"[ok]   {slug}: all variables resolved")

    print("\n=== Contrast Summary ===")
    for slug in slugs:
        failures = contrast_map.get(slug, [])
        if not failures:
            print(f"[ok]   {slug}: all tracked pairs pass WCAG thresholds")
        else:
            print(f"[warn] {slug}: {len(failures)} contrast pairs below threshold")
            for desc, ratio, required in failures:
                print(f"   - {desc}: {ratio:.2f} (requires {required:.1f})")

    if args.report:
        ensure_dir(Path(args.report).parent)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "themes": {}
        }
        for slug in slugs:
            payload["themes"][slug] = {
                "missing": missing_map.get(slug, []),
                "contrast_failures": [
                    {
                        "pair": desc,
                        "ratio": round(ratio, 2),
                        "required": required,
                    }
                    for desc, ratio, required in contrast_map.get(slug, [])
                ],
            }
        Path(args.report).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n[info] wrote contrast report to {args.report}")

    if args.md_report:
        ensure_dir(Path(args.md_report).parent)
        lines = ["# Theme Contrast Report", ""]
        lines.append(f"Generated {datetime.now(timezone.utc).isoformat()}")
        lines.append("")
        for slug in slugs:
            lines.append(f"## {slug}")
            missing = missing_map.get(slug, [])
            if missing:
                lines.append("- Missing tokens (fallback applied):")
                for name in missing:
                    lines.append(f"  - `{name}`")
            failures = contrast_map.get(slug, [])
            if failures:
                lines.append("- Contrast issues:")
                for desc, ratio, required in failures:
                    lines.append(f"  - {desc}: **{ratio:.2f}** (needs {required:.1f})")
            if not missing and not failures:
                lines.append("- ✅ All checks passed")
            lines.append("")
        Path(args.md_report).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"[info] wrote Markdown report to {args.md_report}")


if __name__ == "__main__":
    main()

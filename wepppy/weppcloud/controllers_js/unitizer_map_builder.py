"""Helpers to generate the static unitizer map ES module.

This module extracts category/unit metadata and conversion definitions from
``wepppy.nodb.unitizer`` without importing the full ``wepppy.nodb`` package
tree (which pulls in optional raster dependencies).  The generated structure
drives both the controllers bundle and the unitizer modal.

The public entry points intentionally accept/return plain Python data
structures so tests can assert parity with the runtime implementation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable, Dict, Iterable, List, MutableMapping, Tuple
import importlib.util
import json
import sys
import types


ROOT = Path(__file__).resolve().parents[3]
UNITIZER_PATH = ROOT / "wepppy" / "nodb" / "unitizer.py"
DEFAULT_OUTPUT_PATH = ROOT / "wepppy" / "weppcloud" / "static" / "js" / "unitizer_map.js"


UnitConverter = Callable[[float], float]


@dataclass(frozen=True)
class LinearTransform:
    """Affine transformation ``y = scale * x + offset``."""

    scale: float
    offset: float

    def apply(self, value: float) -> float:
        return self.scale * value + self.offset

    def compose(self, following: "LinearTransform") -> "LinearTransform":
        """Return a transform equivalent to ``following(self(x))``."""
        return LinearTransform(
            scale=following.scale * self.scale,
            offset=following.scale * self.offset + following.offset,
        )

    def inverse(self) -> "LinearTransform":
        if self.scale == 0:
            raise ValueError("Cannot invert transform with zero scale")
        inv_scale = 1.0 / self.scale
        return LinearTransform(scale=inv_scale, offset=-self.offset * inv_scale)


def _stub_wepppy_modules() -> None:
    """Install lightweight stubs so unitizer.py can execute in isolation."""

    if "wepppy" in sys.modules:
        return

    root_pkg = types.ModuleType("wepppy")
    root_pkg.__path__ = [str(ROOT / "wepppy")]
    sys.modules["wepppy"] = root_pkg

    nodb_pkg = types.ModuleType("wepppy.nodb")
    nodb_pkg.__path__ = [str(ROOT / "wepppy" / "nodb")]
    sys.modules["wepppy.nodb"] = nodb_pkg

    base_mod = types.ModuleType("wepppy.nodb.base")

    class _DummyNoDbBase:
        def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - trivial
            pass

    base_mod.NoDbBase = _DummyNoDbBase
    sys.modules["wepppy.nodb.base"] = base_mod

    helpers_mod = types.ModuleType("wepppy.all_your_base")

    def _isfloat(value: object) -> bool:
        try:
            float(value)
            return True
        except Exception:
            return False

    def _isnan(value: object) -> bool:
        try:
            return float(value) != float(value)
        except Exception:
            return False

    helpers_mod.isfloat = _isfloat  # type: ignore[attr-defined]
    helpers_mod.isnan = _isnan  # type: ignore[attr-defined]
    sys.modules["wepppy.all_your_base"] = helpers_mod


def load_unitizer_module():
    """Load ``wepppy.nodb.unitizer`` with minimal dependency scaffolding."""

    _stub_wepppy_modules()
    spec = importlib.util.spec_from_file_location(
        "wepppy.nodb.unitizer", str(UNITIZER_PATH)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load spec for {UNITIZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["wepppy.nodb.unitizer"] = module
    spec.loader.exec_module(module)
    return module


def _cls_units(units: str) -> str:
    """Mirror unitizer.cls_units."""
    return (
        str(units)
        .replace("/", "_")
        .replace("^2", "-sqr")
        .replace("^3", "-cube")
        .replace(",", "-_")
    )


def _plain_units(units: str) -> str:
    """Return a plain-text unit label (commas signal variant suffixes)."""
    return str(units).split(",")[0]


def _html_units(units: str) -> str:
    """Return the HTML label variant (superscripts for powers)."""
    base = _plain_units(units)
    return base.replace("^2", "<sup>2</sup>").replace("^3", "<sup>3</sup>")


def _friendly_category_name(key: str) -> str:
    parts = key.replace("_", " ").replace("-", " ").split()
    if not parts:
        return key
    return " ".join(part.capitalize() for part in parts)


def _derive_linear_params(func: UnitConverter) -> LinearTransform:
    """Sample converter at 0 and 1 to recover scale/offset."""
    base = float(func(0.0))
    sample = float(func(1.0))
    scale = sample - base
    return LinearTransform(scale=scale, offset=base)


def _round_float(value: float) -> float:
    # Use a stable rounding to avoid noisy representations in the JS output.
    return float(f"{value:.12g}")


def _collect_transforms(
    unit_keys: Iterable[str],
    raw_converters: MutableMapping[Tuple[str, str], LinearTransform],
) -> Dict[Tuple[str, str], LinearTransform]:
    """Ensure every ordered unit pair has a transform by composing paths."""

    transforms: Dict[Tuple[str, str], LinearTransform] = dict(raw_converters)

    for src, dst in list(transforms):
        reverse_key = (dst, src)
        if reverse_key not in transforms:
            transforms[reverse_key] = transforms[(src, dst)].inverse()

    units = list(unit_keys)
    adjacency: Dict[str, List[Tuple[str, LinearTransform]]] = {}
    for (src, dst), transform in transforms.items():
        adjacency.setdefault(src, []).append((dst, transform))

    for src in units:
        for dst in units:
            if src == dst or (src, dst) in transforms:
                continue
            derived = _find_composed_transform(src, dst, adjacency)
            if derived is None:
                raise RuntimeError(f"No conversion path between {src!r} and {dst!r}")
            transforms[(src, dst)] = derived
            adjacency.setdefault(src, []).append((dst, derived))

    return transforms


def _find_composed_transform(
    src: str,
    dst: str,
    adjacency: Dict[str, List[Tuple[str, LinearTransform]]],
) -> LinearTransform | None:
    """Breadth-first search to compose available linear transforms."""

    queue: deque[Tuple[str, LinearTransform]] = deque()
    visited: Dict[str, LinearTransform] = {}

    for neighbor, edge in adjacency.get(src, []):
        queue.append((neighbor, edge))
        visited[neighbor] = edge

    while queue:
        current, transform = queue.popleft()
        if current == dst:
            return transform
        for neighbor, edge in adjacency.get(current, []):
            if neighbor in visited:
                continue
            composed = transform.compose(edge)
            visited[neighbor] = composed
            queue.append((neighbor, composed))
    return None


def build_unitizer_map_data() -> Dict[str, object]:
    """Return the structured metadata used by the ES module."""

    unitizer = load_unitizer_module()
    converters = unitizer.converters
    precisions = unitizer.precisions

    categories: List[Dict[str, object]] = []
    token_to_canonical: Dict[str, str] = {}
    canonical_to_category: Dict[str, str] = {}

    for category_key, units in precisions.items():
        unit_order = list(units.keys())

        unit_set = set(unit_order)
        raw_transforms: Dict[Tuple[str, str], LinearTransform] = {}
        for (src, dst), func in converters[category_key].items():
            if src not in unit_set or dst not in unit_set:
                continue
            transform = _derive_linear_params(func)
            raw_transforms[(src, dst)] = transform

        transforms = _collect_transforms(unit_order, raw_transforms)

        unit_entries = []
        for unit_key in unit_order:
            token = _cls_units(unit_key)
            token_to_canonical[token] = unit_key
            canonical_to_category[unit_key] = category_key
            unit_entries.append(
                {
                    "key": unit_key,
                    "token": token,
                    "label": _plain_units(unit_key),
                    "htmlLabel": _html_units(unit_key),
                    "precision": int(units[unit_key]),
                }
            )

        conversion_entries = []
        for (src, dst), transform in sorted(transforms.items()):
            if src == dst:
                continue
            conversion_entries.append(
                {
                    "from": src,
                    "to": dst,
                    "scale": _round_float(transform.scale),
                    "offset": _round_float(transform.offset),
                }
            )

        categories.append(
            {
                "key": category_key,
                "label": _friendly_category_name(category_key),
                "defaultIndex": 1 if len(unit_entries) > 1 else 0,
                "units": unit_entries,
                "conversions": conversion_entries,
            }
        )

    map_data = {
        "categories": categories,
        "tokenToUnit": token_to_canonical,
        "unitToCategory": canonical_to_category,
        "generator": "unitizer_map_builder.py",
    }

    return map_data


def render_unitizer_module(map_data: Dict[str, object]) -> str:
    """Serialize the map as an ES module."""

    payload = json.dumps(map_data, indent=2, sort_keys=True, ensure_ascii=True)
    return dedent(
        f"""\
        /* ----------------------------------------------------------------------------
         * Unitizer Static Map (generated by unitizer_map_builder.py)
         * ----------------------------------------------------------------------------
         */
        export const unitizerMap = Object.freeze({payload});

        export function getUnitizerMap() {{
          return unitizerMap;
        }}

        if (typeof window !== "undefined") {{
          window.__unitizerMap = unitizerMap;
        }}
        """
    )


def write_unitizer_module(
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, object]:
    """Build the map data and write the ES module to ``output_path``."""

    map_data = build_unitizer_map_data()
    contents = render_unitizer_module(map_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(contents, encoding="utf-8")
    return map_data


__all__ = [
    "DEFAULT_OUTPUT_PATH",
    "LinearTransform",
    "build_unitizer_map_data",
    "load_unitizer_module",
    "render_unitizer_module",
    "write_unitizer_module",
]

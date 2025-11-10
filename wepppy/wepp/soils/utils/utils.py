"""Utility helpers for manipulating WEPP soil lookup tables and files."""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from typing import Dict, List, MutableMapping, Optional, Tuple

from deprecated import deprecated

__all__ = [
    "SoilReplacements",
    "read_lc_file",
    "simple_texture",
    "simple_texture_enum",
    "soil_texture",
    "soil_specialization",
    "modify_kslast",
    "soil_is_water",
]


@dataclass
class SoilReplacements:
    """Container describing per-parameter overrides applied to a soil file."""

    Code: Optional[int] = None
    LndcvrID: Optional[int] = None
    WEPP_Type: Optional[str] = None
    New_WEPPman: Optional[str] = None
    ManName: Optional[str] = None
    Albedo: Optional[str] = None
    iniSatLev: Optional[str] = None
    interErod: Optional[str] = None
    rillErod: Optional[str] = None
    critSh: Optional[str] = None
    effHC: Optional[str] = None
    soilDepth: Optional[str] = None
    Sand: Optional[str] = None
    Clay: Optional[str] = None
    OM: Optional[str] = None
    CEC: Optional[str] = None
    Comment: Optional[str] = None
    fname: Optional[str] = None
    kslast: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover - retained for backward compat
        fields = [
            f"{name}={value}"
            for name, value in self.__dict__.items()
            if value is not None
        ]
        return f"SoilReplacements({' '.join(fields)})"


@deprecated
def read_lc_file(fname: str) -> Dict[Tuple[str, str], MutableMapping[str, Optional[str]]]:
    """Return land-cover parameters keyed by ``(LndcvrID, WEPP_Type)``.

    Args:
        fname: Path to a WEPP land-cover CSV file.

    Returns:
        A mapping whose keys are the ``(LndcvrID, WEPP_Type)`` tuple and whose
        values contain the entire CSV row with ``"none*"`` entries normalized to
        ``None``.
    """
    result: Dict[Tuple[str, str], MutableMapping[str, Optional[str]]] = {}

    with open(fname, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["Code"] = int(row["Code"])
            row["LndcvrID"] = int(row["LndcvrID"])
            row["fname"] = fname

            for key, value in list(row.items()):
                if isinstance(value, str) and value.lower().startswith("none"):
                    row[key] = None

            result[(str(row["LndcvrID"]), row["WEPP_Type"])] = row

    return result


def _replace_parameter(original: str, replacement: Optional[str]) -> str:
    """Return ``replacement`` while supporting multiplicative ``*`` syntax."""
    if replacement is None:
        return original

    stripped = replacement.strip()
    if stripped.startswith("*"):
        multiplier = float(stripped.replace("*", "", 1))
        return str(float(original) * multiplier)

    return replacement


def simple_texture(clay: float, sand: float) -> Optional[str]:
    """Classify soil texture into coarse categories (loam, sand loam, etc.).

    Args:
        clay: Clay percentage (0-100).
        sand: Sand percentage (0-100).

    Returns:
        A simplified text label or ``None`` when no coarse class matches.
    """
    cs = clay + sand
    if (clay <= 27.0 and cs <= 50.0) or (clay > 27.0 and sand <= 20.0 and cs <= 50.0):
        return "silt loam"
    if (6.0 <= clay <= 27.0) and (50.0 < cs <= 72.0) and sand <= 52:
        return "loam"
    if (sand > 52 or cs > 50 and clay < 6) and sand >= 50:
        return "sand loam"
    if (cs > 72 and sand < 50) or (clay > 27 and (20 < sand <= 45)) or (sand <= 20 and cs > 50):
        return "clay loam"

    tex = soil_texture(clay, sand)
    if tex.startswith("sand"):
        return "sand loam"
    if tex.startswith("silt"):
        return "silt loam"
    if tex.startswith("clay"):
        return "clay loam"
    if tex.startswith("loam"):
        return "loam"
    return None


def simple_texture_enum(clay: float, sand: float) -> int:
    """Return the integer enum corresponding to :func:`simple_texture`.

    Args:
        clay: Clay percentage (0-100).
        sand: Sand percentage (0-100).

    Returns:
        Integer identifier matching WEPP's coarse texture categories.

    Raises:
        ValueError: If :func:`simple_texture` cannot classify the inputs.
    """
    mapping = {"clay loam": 1, "loam": 2, "sand loam": 3, "silt loam": 4}
    texture = simple_texture(clay, sand)
    if texture is None:
        raise ValueError("Unable to classify texture")  # pragma: no cover - defensive
    return mapping[texture]


def _soil_texture(clay: float, sand: float) -> Optional[str]:
    """Return the detailed USDA soil texture classification."""
    assert sand + clay <= 100
    silt = 100.0 - sand - clay

    if clay >= 40:
        if silt >= 40:
            return "silty clay"
        if sand <= 45:
            return "clay"

    if clay >= 35 and sand > 45:
        return "sandy clay"

    if clay >= 27:
        if sand <= 20:
            return "silty clay loam"
        if sand <= 45:
            return "clay loam"
    else:
        if silt >= 50:
            if clay < 12.0 and silt >= 80:
                return "silt"
            return "silt loam"
        if silt >= 28 and clay >= 7 and sand <= 52:
            return "loam"

    if clay >= 20 and sand > 45 and silt <= 28:
        return "sandy clay loam"

    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    return "sandy loam"


def soil_texture(clay: float, sand: float) -> str:
    """Return the detailed USDA soil texture classification."""
    result = _soil_texture(clay, sand)
    assert result is not None
    return result


@deprecated
def soil_specialization(src: str, dst: str, replacements: SoilReplacements, caller: str = "") -> None:
    """Create a new soil file with selected parameters replaced.

    Args:
        src: Source soil file to read.
        dst: Destination path for the modified soil.
        replacements: Structured overrides applied to header/horizon fields.
        caller: Optional provenance string stored in the header.
    """
    with open(src) as f:
        lines = f.readlines()

    header = [line for line in lines if line.startswith("#")]
    header.append(
        f"# {f'{caller}:' if caller else ''}soil_specialization({replacements!r})\n"
    )

    lines = [line for line in lines if not line.startswith("#")]

    line4 = lines[3].split()
    line4[-6] = _replace_parameter(line4[-6], replacements.Albedo)
    line4[-5] = _replace_parameter(line4[-5], replacements.iniSatLev)
    line4[-4] = _replace_parameter(line4[-4], replacements.interErod)
    line4[-3] = _replace_parameter(line4[-3], replacements.rillErod)
    line4[-2] = _replace_parameter(line4[-2], replacements.critSh)
    line4 = " ".join(line4) + "\n"

    line5 = lines[4].split()
    line5[2] = _replace_parameter(line5[2], replacements.effHC)

    if len(line5) < 5:
        shutil.copyfile(src, dst)
        return

    if "rock" not in lines[3].lower() and "water" not in lines[3].lower():
        line5[6] = _replace_parameter(line5[6], replacements.Sand)
        line5[7] = _replace_parameter(line5[7], replacements.Clay)
        line5[8] = _replace_parameter(line5[8], replacements.OM)
        line5[9] = _replace_parameter(line5[9], replacements.CEC)
    line5 = " ".join(line5) + "\n"

    if replacements.kslast is not None and len(lines) > 5 and len(lines[-1].split()) == 3:
        lastline = lines[-1].split()
        lastline[-1] = f"{replacements.kslast}"
        lines[-1] = " ".join(lastline)

    with open(dst, "w") as f:
        f.writelines(header)
        f.writelines(lines[:3])
        f.writelines(line4)
        f.writelines(line5)
        if len(lines) > 5:
            f.writelines(lines[5:])


def modify_kslast(src: str, dst: str, kslast: float, caller: str = "") -> None:
    """Write a copy of ``src`` to ``dst`` using ``kslast`` for the restrictive layer.

    Args:
        src: Source soil file path.
        dst: Destination soil file path.
        kslast: Replacement restrictive layer conductivity value.
        caller: Optional provenance string stored in the header.
    """
    with open(src) as fp:
        lines = fp.readlines()

    while lines and not lines[-1].strip():
        lines.pop()

    header = [line for line in lines if line.startswith("#")]
    header.append(f"# {f'{caller}:' if caller else ''}modify_kslast({kslast})\n")

    lines = [line for line in lines if not line.startswith("#")]

    lastline = lines[-1].split()
    lastline[-1] = f"{kslast}"
    lines[-1] = " ".join(lastline)

    with open(dst, "w") as fp:
        fp.writelines(header)
        fp.writelines(lines)


def soil_is_water(soil_fn: str) -> bool:
    """Return True when ``soil_fn`` describes a water body rather than soil.

    Args:
        soil_fn: Soil file path to inspect.

    Returns:
        True if ``soil_fn`` contains ``"water"`` (case insensitive), otherwise
        False.
    """
    with open(soil_fn) as fp2:
        contents = fp2.read()
    return "water" in contents.lower()

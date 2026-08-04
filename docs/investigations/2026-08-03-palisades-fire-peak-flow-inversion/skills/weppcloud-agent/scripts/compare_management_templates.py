#!/usr/bin/env python3
"""
Compare two WEPP .man management templates (focused on Cropland plant+initial blocks).

This is intentionally lightweight (stdlib only) so it can run in the local uv venv
without pulling in wepppy/wepp imports (which may require optional deps).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple


def _strip_comment(raw: str) -> str:
    return raw.split("#", 1)[0].strip()


def _nonempty_tokens(lines: Iterable[str]) -> Iterator[List[str]]:
    for raw in lines:
        s = _strip_comment(raw)
        if not s:
            continue
        yield s.split()


def _take(tokens_iter: Iterator[List[str]], n: int) -> List[str]:
    out: List[str] = []
    while len(out) < n:
        out.extend(next(tokens_iter))
    return out[:n]


def _take_group(tokens_iter: Iterator[List[str]], allowed_lengths: Tuple[int, ...]) -> List[str]:
    toks = next(tokens_iter)
    if len(toks) not in allowed_lengths:
        raise ValueError(f"Unexpected token-group length {len(toks)}; expected {allowed_lengths}")
    return toks


@dataclass(frozen=True)
class ParsedMan:
    plant: List[Tuple[str, str]]
    ini: List[Tuple[str, str]]


PLANT_CROPLAND_FIELDS_10 = [
    "bb",
    "bbb",
    "beinp",
    "btemp",
    "cf",
    "crit",
    "critvm",
    "cuthgt",
    "decfct",
    "diam",
]
PLANT_CROPLAND_FIELDS_8 = [
    "dlai",
    "dropfc",
    "extnct",
    "fact",
    "flivmx",
    "gddmax",
    "hi",
    "hmax",
]
PLANT_CROPLAND_FIELDS_10B = [
    "oratea",
    "orater",
    "otemp",
    "pltol",
    "pltsp",
    "rdmax",
    "rsr",
    "rtmmax",
    "spriod",
    "tmpmax",
]
PLANT_CROPLAND_FIELDS_3_OR_4 = [
    "tmpmin",
    "xmxlai",
    "yld",
    "rcc",
]

INI_CROPLAND_FIELDS_6 = [
    "bdtill",
    "cancov",
    "daydis",
    "dsharv",
    "frdp",
    "inrcov",
]
INI_CROPLAND_FIELDS_5 = [
    "rfcum",
    "rhinit",
    "rilcov",
    "rrinit",
    "rspace",
]
INI_CROPLAND_FIELDS_5B = [
    "snodpy",
    "thdp",
    "tillay1",
    "tillay2",
    "width",
]
INI_CROPLAND_FIELDS_2_OR_4 = [
    "sumrtm",
    "sumsrm",
    "usinrco",
    "usrilco",
]


def _parse_first_plant_and_ini(man_path: Path) -> ParsedMan:
    tokens = list(_nonempty_tokens(man_path.read_text().splitlines()))
    # We parse by scanning for the section headers and then consuming the
    # first scenario (these templates are 1-scenario files).
    #
    # The parsing strategy avoids assuming fixed line numbers and tolerates
    # blank/comment lines.
    def find_index(needle: str) -> int:
        for i, toks in enumerate(tokens):
            if toks and toks[0] == needle:
                return i
        raise ValueError(f"Could not find token {needle!r} in {man_path}")

    # Locate the first "WeppWillSet" which is the crunit marker under the first
    # plant scenario in WEPP cropland-style plant sections.
    crunit_i = None
    for i, toks in enumerate(tokens):
        if toks and toks[0] == "WeppWillSet":
            crunit_i = i
            break
    if crunit_i is None:
        raise ValueError(f"Failed to locate Plant crunit (WeppWillSet) in {man_path}")

    plant_values: List[Tuple[str, str]] = []
    # Numeric blocks occur immediately after crunit.
    it = iter(tokens[crunit_i + 1 :])
    vals10 = _take_group(it, (10,))
    plant_values.extend(list(zip(PLANT_CROPLAND_FIELDS_10, vals10)))
    vals8 = _take_group(it, (8,))
    plant_values.extend(list(zip(PLANT_CROPLAND_FIELDS_8, vals8)))
    mfocod = _take_group(it, (1,))[0]
    plant_values.append(("mfocod", mfocod))
    vals10b = _take_group(it, (10,))
    plant_values.extend(list(zip(PLANT_CROPLAND_FIELDS_10B, vals10b)))
    tail = _take_group(it, (3, 4))
    plant_values.extend(list(zip(PLANT_CROPLAND_FIELDS_3_OR_4[: len(tail)], tail)))

    # Initial Conditions: find the Ini cropland 6-field block after the plant block.
    # We search the remainder for a 6-token group with integer daydis/dsharv.
    ini_start_i: Optional[int] = None
    remainder = tokens[crunit_i + 1 :]
    for i, toks in enumerate(remainder):
        if len(toks) != 6:
            continue
        # daydis, dsharv are integers in WEPP .man
        if toks[2].isdigit() and toks[3].isdigit():
            # Heuristic: bdtill and cancov are floats.
            if "." in toks[0] and "." in toks[1]:
                ini_start_i = (crunit_i + 1) + i
                break
    if ini_start_i is None:
        raise ValueError(f"Failed to locate Ini cropland 6-field block in {man_path}")

    ini_values: List[Tuple[str, str]] = []
    it2 = iter(tokens[ini_start_i:])
    ini6 = _take_group(it2, (6,))
    ini_values.extend(list(zip(INI_CROPLAND_FIELDS_6, ini6)))
    iresd = _take_group(it2, (1,))[0]
    ini_values.append(("iresd", iresd))
    imngmt = _take_group(it2, (1,))[0]
    ini_values.append(("imngmt", imngmt))
    ini5 = _take_group(it2, (5,))
    ini_values.extend(list(zip(INI_CROPLAND_FIELDS_5, ini5)))
    rtyp = _take_group(it2, (1,))[0]
    ini_values.append(("rtyp", rtyp))
    ini5b = _take_group(it2, (5,))
    ini_values.extend(list(zip(INI_CROPLAND_FIELDS_5B, ini5b)))
    ini_tail = _take_group(it2, (2, 4))
    ini_values.extend(list(zip(INI_CROPLAND_FIELDS_2_OR_4[: len(ini_tail)], ini_tail)))

    return ParsedMan(plant=plant_values, ini=ini_values)


def _latex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def _to_table_tex(
    rows: List[Tuple[str, str, str, str]],
    caption: str,
    label: str,
) -> str:
    out: List[str] = []
    out.append("\\begin{table}[p]")
    out.append("  \\centering")
    out.append("  \\small")
    out.append(f"  \\caption{{{caption}}}")
    out.append(f"  \\label{{{label}}}")
    out.append("  \\begin{tabular}{l r r r}")
    out.append("    \\toprule")
    out.append("    Parameter & Unburned & Burned (moderate) & $\\Delta$ (B--U) \\\\")
    out.append("    \\midrule")
    for param, u, b, d in rows:
        out.append(f"    {_latex_escape(param)} & {u} & {b} & {d} \\\\")
    out.append("    \\bottomrule")
    out.append("  \\end{tabular}")
    out.append("\\end{table}")
    return "\n".join(out)


def _fmt_delta(u: str, b: str) -> str:
    try:
        du = float(u)
        db = float(b)
    except ValueError:
        return ""
    return f"{(db - du):0.5g}"


def _rows_for_section(
    u_pairs: List[Tuple[str, str]],
    b_pairs: List[Tuple[str, str]],
) -> List[Tuple[str, str, str, str]]:
    u = dict(u_pairs)
    b = dict(b_pairs)
    keys = sorted(set(u) | set(b))
    rows: List[Tuple[str, str, str, str]] = []
    for k in keys:
        uval = u.get(k, "")
        bval = b.get(k, "")
        d = _fmt_delta(uval, bval)
        rows.append((k, uval, bval, d))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unburned", type=Path, required=True)
    ap.add_argument("--burned", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    unburned = _parse_first_plant_and_ini(args.unburned)
    burned = _parse_first_plant_and_ini(args.burned)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Plant + ini longtables.
    plant_rows = _rows_for_section(unburned.plant, burned.plant)
    ini_rows = _rows_for_section(unburned.ini, burned.ini)

    plant_tex = _to_table_tex(
        plant_rows,
        caption="WEPP Cropland plant parameters: Shrub.man (unburned) vs. Shrub\\_Moderate\\_Severity\\_Fire.man",
        label="tab:shrub_plant_params",
    )
    ini_tex = _to_table_tex(
        ini_rows,
        caption="WEPP Cropland initial-condition parameters: Shrub.man (unburned) vs. Shrub\\_Moderate\\_Severity\\_Fire.man",
        label="tab:shrub_ini_params",
    )

    (args.out_dir / "shrub_plant_params_longtable.tex").write_text(plant_tex)
    (args.out_dir / "shrub_ini_params_longtable.tex").write_text(ini_tex)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

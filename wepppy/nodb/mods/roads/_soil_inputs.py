"""Native Roads soil assembly; facade callbacks preserve retained parameterization and readback."""

from __future__ import annotations

from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
import shlex
from pathlib import Path
from typing import List, Sequence, Tuple


def _build_routed_mofe_soil_file(
    self,
    *,
    template_path: Path,
    output_path: Path,
    traffic: str,
    surface: str,
    rfg_pct: float,
    ofe_order: Sequence[int],
) -> None:
    if not ofe_order:
        raise ValueError("ofe_order must not be empty")
    if any(index not in {1, 2, 3} for index in ofe_order):
        raise ValueError("ofe_order entries must be one of 1 (road), 2 (fill), or 3 (hill/forest).")

    lines = template_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 10:
        raise ValueError(f"Roads soil template is malformed: {template_path}")

    out: List[str] = []
    i = 0
    out.append(lines[i])
    i += 1

    while i < len(lines) and lines[i].startswith("#"):
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing soil comment): {template_path}")
    out.append(lines[i])
    i += 1

    while i < len(lines) and not lines[i].strip():
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing ntemp line): {template_path}")
    ntemp_tokens = lines[i].split()
    ksflag = ntemp_tokens[1] if len(ntemp_tokens) > 1 else "0"
    out.append(f"{len(ofe_order)} {ksflag}")
    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    ofe_pairs: List[Tuple[str, str]] = []
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        if i + 1 >= len(lines):
            raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
        ofe_pairs.append((lines[i], lines[i + 1]))
        i += 2

    if len(ofe_pairs) < 3:
        raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

    urr_ref = 95.0 if surface == "paved" else 65.0
    ufr_ref = (float(rfg_pct) + 65.0) / 2.0

    for scenario_idx in ofe_order:
        header, horizon = ofe_pairs[int(scenario_idx) - 1]
        if int(scenario_idx) == 1:
            road_tokens = shlex.split(header)
            if len(road_tokens) < 8:
                raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
            slid, texid = road_tokens[0], road_tokens[1]
            nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
            avke = road_tokens[8] if len(road_tokens) > 8 else None

            ki_value = float(ki)
            kr_value = float(kr)
            if traffic != "high":
                ki_value /= 4.0
                kr_value /= 4.0

            header_line = f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
            if avke is not None:
                header_line += f" {avke}"
        else:
            header_line = header

        horizon_line = self._replace_soil_marker(
            horizon,
            urr_ref=urr_ref,
            ufr_ref=ufr_ref,
            ubr_value=float(rfg_pct),
        )

        out.append(header_line)
        out.append(horizon_line)

    output_path.write_text(ensure_200mm_boundary("\n".join(out) + "\n"), encoding="utf-8")
    self._apply_parameterization_to_soil(output_path, template_path, traffic, ofe_order)


def _replace_soil_marker(
    horizon_line: str,
    *,
    urr_ref: float,
    ufr_ref: float,
    ubr_value: float,
) -> str:
    tokens = horizon_line.split()
    if not tokens:
        return horizon_line
    marker = tokens[-1].lower()
    if marker == "urr":
        tokens[-1] = f"{float(urr_ref):.6g}"
    elif marker == "ufr":
        tokens[-1] = f"{float(ufr_ref):.6g}"
    elif marker == "ubr":
        tokens[-1] = f"{float(ubr_value):.6g}"
    return " ".join(tokens)


def _build_routed_two_ofe_soil_file(
    self,
    *,
    template_path: Path,
    output_path: Path,
    traffic: str,
    surface: str,
    rfg_pct: float,
) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 8:
        raise ValueError(f"Roads soil template is malformed: {template_path}")

    out: List[str] = []
    i = 0
    out.append(lines[i])
    i += 1

    while i < len(lines) and lines[i].startswith("#"):
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing soil comment): {template_path}")
    out.append(lines[i])
    i += 1

    while i < len(lines) and not lines[i].strip():
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing ntemp line): {template_path}")
    ntemp_tokens = lines[i].split()
    ksflag = ntemp_tokens[1] if len(ntemp_tokens) > 1 else "0"
    out.append(f"2 {ksflag}")
    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    ofe_pairs: List[Tuple[str, str]] = []
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        if i + 1 >= len(lines):
            raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
        ofe_pairs.append((lines[i], lines[i + 1]))
        i += 2

    if len(ofe_pairs) < 3:
        raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

    road_header, road_horizon = ofe_pairs[0]
    buffer_header, buffer_horizon = ofe_pairs[2]
    road_tokens = shlex.split(road_header)
    if len(road_tokens) < 8:
        raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
    slid, texid = road_tokens[0], road_tokens[1]
    nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
    avke = road_tokens[8] if len(road_tokens) > 8 else None

    ki_value = float(ki)
    kr_value = float(kr)
    if traffic != "high":
        ki_value /= 4.0
        kr_value /= 4.0

    road_header_line = (
        f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
    )
    if avke is not None:
        road_header_line += f" {avke}"

    urr_ref = 95.0 if surface == "paved" else 65.0
    ufr_ref = (float(rfg_pct) + 65.0) / 2.0
    road_horizon_line = self._replace_soil_marker(
        road_horizon,
        urr_ref=urr_ref,
        ufr_ref=ufr_ref,
        ubr_value=float(rfg_pct),
    )
    buffer_horizon_line = self._replace_soil_marker(
        buffer_horizon,
        urr_ref=urr_ref,
        ufr_ref=ufr_ref,
        ubr_value=float(rfg_pct),
    )

    out.append(road_header_line)
    out.append(road_horizon_line)
    out.append(buffer_header)
    out.append(buffer_horizon_line)
    output_path.write_text(ensure_200mm_boundary("\n".join(out) + "\n"), encoding="utf-8")
    self._apply_parameterization_to_soil(output_path, template_path, traffic, (1, 3))


def _build_routed_three_ofe_soil_file(
    self,
    *,
    template_path: Path,
    output_path: Path,
    traffic: str,
    surface: str,
    rfg_pct: float,
) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 10:
        raise ValueError(f"Roads soil template is malformed: {template_path}")

    out: List[str] = []
    i = 0
    out.append(lines[i])
    i += 1

    while i < len(lines) and lines[i].startswith("#"):
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing soil comment): {template_path}")
    out.append(lines[i])
    i += 1

    while i < len(lines) and not lines[i].strip():
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing ntemp line): {template_path}")
    ntemp_tokens = lines[i].split()
    ksflag = ntemp_tokens[1] if len(ntemp_tokens) > 1 else "0"
    out.append(f"3 {ksflag}")
    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    ofe_pairs: List[Tuple[str, str]] = []
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        if i + 1 >= len(lines):
            raise ValueError(f"Roads soil template has incomplete OFE pair: {template_path}")
        ofe_pairs.append((lines[i], lines[i + 1]))
        i += 2

    if len(ofe_pairs) < 3:
        raise ValueError(f"Roads soil template must include at least three OFEs: {template_path}")

    road_header, road_horizon = ofe_pairs[0]
    fill_header, fill_horizon = ofe_pairs[1]
    buffer_header, buffer_horizon = ofe_pairs[2]

    road_tokens = shlex.split(road_header)
    if len(road_tokens) < 8:
        raise ValueError(f"Roads soil template has malformed road OFE header: {template_path}")
    slid, texid = road_tokens[0], road_tokens[1]
    nsl, salb, sat, ki, kr, shcrit = road_tokens[2:8]
    avke = road_tokens[8] if len(road_tokens) > 8 else None

    ki_value = float(ki)
    kr_value = float(kr)
    if traffic != "high":
        ki_value /= 4.0
        kr_value /= 4.0

    road_header_line = (
        f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
    )
    if avke is not None:
        road_header_line += f" {avke}"

    urr_ref = 95.0 if surface == "paved" else 65.0
    ufr_ref = (float(rfg_pct) + 65.0) / 2.0
    road_horizon_line = self._replace_soil_marker(
        road_horizon,
        urr_ref=urr_ref,
        ufr_ref=ufr_ref,
        ubr_value=float(rfg_pct),
    )
    fill_horizon_line = self._replace_soil_marker(
        fill_horizon,
        urr_ref=urr_ref,
        ufr_ref=ufr_ref,
        ubr_value=float(rfg_pct),
    )
    buffer_horizon_line = self._replace_soil_marker(
        buffer_horizon,
        urr_ref=urr_ref,
        ufr_ref=ufr_ref,
        ubr_value=float(rfg_pct),
    )

    out.append(road_header_line)
    out.append(road_horizon_line)
    out.append(fill_header)
    out.append(fill_horizon_line)
    out.append(buffer_header)
    out.append(buffer_horizon_line)
    output_path.write_text(ensure_200mm_boundary("\n".join(out) + "\n"), encoding="utf-8")
    self._apply_parameterization_to_soil(output_path, template_path, traffic, (1, 2, 3))


def _build_single_ofe_soil_file(
    self,
    *,
    template_path: Path,
    output_path: Path,
    traffic: str,
    surface: str,
    rfg_pct: float,
) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 6:
        raise ValueError(f"Roads soil template is malformed: {template_path}")

    out: List[str] = []
    i = 0
    out.append(lines[i])
    i += 1

    while i < len(lines) and lines[i].startswith("#"):
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing soil comment): {template_path}")
    out.append(lines[i])
    i += 1

    while i < len(lines) and not lines[i].strip():
        out.append(lines[i])
        i += 1

    if i >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing ntemp line): {template_path}")
    ntemp_tokens = lines[i].split()
    ksflag = ntemp_tokens[1] if len(ntemp_tokens) > 1 else "0"
    out.append(f"1 {ksflag}")
    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    if i + 1 >= len(lines):
        raise ValueError(f"Roads soil template is malformed (missing first OFE lines): {template_path}")

    first_ofe_header = lines[i]
    first_ofe_horizon = lines[i + 1]

    header_tokens = shlex.split(first_ofe_header)
    if len(header_tokens) < 8:
        raise ValueError(f"Roads soil template has malformed first OFE header: {template_path}")

    slid, texid = header_tokens[0], header_tokens[1]
    nsl, salb, sat, ki, kr, shcrit = header_tokens[2:8]
    avke = header_tokens[8] if len(header_tokens) > 8 else None

    ki_value = float(ki)
    kr_value = float(kr)
    if traffic != "high":
        ki_value /= 4.0
        kr_value /= 4.0

    header_line = (
        f"'{slid}' '{texid}' {nsl} {salb} {sat} {ki_value:.6g} {kr_value:.6g} {shcrit}"
    )
    if avke is not None:
        header_line += f" {avke}"
    out.append(header_line)

    horizon_tokens = first_ofe_horizon.split()
    if len(horizon_tokens) < 6:
        raise ValueError(f"Roads soil template has malformed first OFE horizon: {template_path}")

    urr_ref = 95.0 if surface == "paved" else 65.0
    marker = horizon_tokens[-1].lower()
    if marker == "urr":
        horizon_tokens[-1] = f"{urr_ref:.6g}"
    elif marker == "ufr":
        horizon_tokens[-1] = f"{((float(rfg_pct) + 65.0) / 2.0):.6g}"
    elif marker == "ubr":
        horizon_tokens[-1] = f"{float(rfg_pct):.6g}"
    out.append(" ".join(horizon_tokens))

    output_path.write_text(ensure_200mm_boundary("\n".join(out) + "\n"), encoding="utf-8")
    self._apply_parameterization_to_soil(output_path, template_path, traffic, (1,))

"""Native Roads management assembly and OFE scenario selection."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


def _extract_ofe_from_nycrop_comment(line: str) -> Optional[int]:
    match = re.search(r"OFE\s*:\s*(\d+)", line)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _build_routed_mofe_management_file(
    self,
    *,
    template_path: Path,
    output_path: Path,
    ofe_order: Sequence[int],
) -> None:
    if not ofe_order:
        raise ValueError("ofe_order must not be empty")
    if any(index not in {1, 2, 3} for index in ofe_order):
        raise ValueError("ofe_order entries must be one of 1 (road), 2 (fill), or 3 (hill/forest).")

    nofe = len(ofe_order)
    lines = template_path.read_text(encoding="utf-8").splitlines()
    out: List[str] = []
    i = 0
    initial_indices_rewritten = False

    while i < len(lines):
        line = lines[i]

        if "# number of OFEs" in line:
            out.append(self._replace_leading_int(line, nofe))
            i += 1
            continue

        if "# `nofe'" in line:
            out.append(self._replace_leading_int(line, nofe))
            i += 1
            continue

        if "# `Initial Conditions indx'" in line and not initial_indices_rewritten:
            original_index_lines: List[str] = []
            while i < len(lines) and "# `Initial Conditions indx'" in lines[i]:
                original_index_lines.append(lines[i])
                i += 1

            if not original_index_lines:
                continue

            for scenario_idx in ofe_order:
                template_line = original_index_lines[min(len(original_index_lines) - 1, scenario_idx - 1)]
                out.append(self._replace_leading_int(template_line, int(scenario_idx)))

            initial_indices_rewritten = True
            continue

        ofe_from_comment = self._extract_ofe_from_nycrop_comment(line)
        if ofe_from_comment is not None and (i + 1) < len(lines) and "# `YEAR indx'" in lines[i + 1]:
            original_pairs: List[Tuple[int, str, str]] = []
            while i < len(lines):
                nycrop_line = lines[i]
                parsed_ofe = self._extract_ofe_from_nycrop_comment(nycrop_line)
                if parsed_ofe is None:
                    break
                if (i + 1) >= len(lines) or "# `YEAR indx'" not in lines[i + 1]:
                    break
                year_line = lines[i + 1]
                original_pairs.append((int(parsed_ofe), nycrop_line, year_line))
                i += 2

            if not original_pairs:
                continue

            pair_map = {ofe_idx: (nycrop_line, year_line) for ofe_idx, nycrop_line, year_line in original_pairs}
            fallback_pair = pair_map.get(3) or pair_map.get(1) or original_pairs[-1][1:]

            for new_ofe_pos, scenario_idx in enumerate(ofe_order, start=1):
                nycrop_line, year_line = pair_map.get(int(scenario_idx), fallback_pair)
                nycrop_line = re.sub(r"(OFE\s*:\s*)\d+", rf"\g<1>{int(new_ofe_pos)}", nycrop_line)
                year_line = self._replace_leading_int(year_line, int(scenario_idx))
                out.append(nycrop_line)
                out.append(year_line)
            continue

        out.append(line)
        i += 1

    output_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _strip_management_scenario_block(
    lines: List[str], *, start_marker: str, end_marker: str
) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if start_marker in line:
            while i < len(lines) and end_marker not in lines[i]:
                i += 1
            continue
        out.append(line)
        i += 1
    return out


def _build_routed_two_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    # Keep all plant definitions and their iresd/itype references intact.
    lines = self._strip_management_scenario_block(
        lines,
        start_marker="Initial Conditions scenario 2 of 3",
        end_marker="Initial Conditions scenario 3 of 3",
    )
    lines = self._strip_management_scenario_block(
        lines,
        start_marker="Yearly scenario 2 of 3",
        end_marker="Yearly scenario 3 of 3",
    )

    out: List[str] = []
    initial_condition_index_counter = 0
    skip_next_year_index = False
    remap_next_year_index = False

    for line in lines:
        if "Initial Conditions scenario 3 of 3" in line:
            line = line.replace("Initial Conditions scenario 3 of 3", "Initial Conditions scenario 2 of 2")
        elif "Yearly scenario 3 of 3" in line:
            line = line.replace("Yearly scenario 3 of 3", "Yearly scenario 2 of 2")

        if (
            "# number of OFEs" in line
            or "# looper; number of Initial Conditions scenarios" in line
            or "# looper; number of Yearly scenarios" in line
            or "# `nofe'" in line
        ):
            line = self._replace_leading_int(line, 2)

        if "# `Initial Conditions indx'" in line:
            initial_condition_index_counter += 1
            if initial_condition_index_counter == 2:
                continue
            if initial_condition_index_counter == 3:
                line = self._replace_leading_int(line, 2)

        if "# `nycrop'" in line and "OFE :" in line:
            if "OFE : 2" in line:
                skip_next_year_index = True
                continue
            if "OFE : 3" in line:
                line = line.replace("OFE : 3", "OFE : 2")
                remap_next_year_index = True

        if skip_next_year_index:
            skip_next_year_index = False
            continue

        if remap_next_year_index and "# `YEAR indx'" in line:
            line = self._replace_leading_int(line, 2)
            remap_next_year_index = False

        out.append(line)

    output_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _materialize_routed_two_ofe_management_template(self, *, traffic: str) -> Path:
    source_path = self._resolve_legacy_management_template_path(traffic=traffic)
    output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.routed_two_ofe.man"
    self._build_routed_two_ofe_management_file(template_path=source_path, output_path=output_path)
    return output_path


def _materialize_routed_three_ofe_management_template(self, *, traffic: str) -> Path:
    source_path = self._resolve_legacy_management_template_path(traffic=traffic)
    output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.routed_three_ofe.man"
    if source_path.resolve() != output_path.resolve():
        shutil.copy2(source_path, output_path)
    return output_path


def _replace_leading_int(line: str, replacement: int) -> str:
    return re.sub(r"^\s*\d+", str(int(replacement)), line, count=1)


def _build_single_ofe_management_file(self, *, template_path: Path, output_path: Path) -> None:
    lines = template_path.read_text(encoding="utf-8").splitlines()
    out: List[str] = []
    i = 0
    replaced_top_nofe = False

    while i < len(lines):
        line = lines[i]
        if "# number of OFEs" in line and not replaced_top_nofe:
            out.append(self._replace_leading_int(line, 1))
            replaced_top_nofe = True
            i += 1
            break
        out.append(line)
        i += 1

    # Plant definitions are referenced by residue and yearly scenarios;
    # their count is independent of the selected OFE count.
    while i < len(lines):
        line = lines[i]
        if "# looper; number of Initial Conditions scenarios" in line:
            out.append(self._replace_leading_int(line, 1))
            i += 1
            break
        out.append(line)
        i += 1

    while i < len(lines):
        if "#\tInitial Conditions scenario 2" in lines[i]:
            break
        out.append(lines[i])
        i += 1

    while i < len(lines) and "###########################" not in lines[i]:
        i += 1

    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        if "# looper; number of Yearly scenarios" in line:
            out[-1] = self._replace_leading_int(line, 1)
            break

    while i < len(lines):
        if "#\tYearly scenario 2" in lines[i]:
            break
        out.append(lines[i])
        i += 1

    while i < len(lines) and "######################" not in lines[i]:
        i += 1

    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        if "# `nofe'" in line:
            out[-1] = self._replace_leading_int(line, 1)
            break

    initial_condition_index_count = 0
    while i < len(lines):
        line = lines[i]
        if "# `Initial Conditions indx'" in line:
            initial_condition_index_count += 1
            if initial_condition_index_count == 1:
                out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
        if "# `nyears'" in line:
            break

    skip_next_year_index = False
    while i < len(lines):
        line = lines[i]
        if "# `nycrop'" in line and "OFE :" in line:
            if "OFE : 1" in line:
                out.append(line)
                skip_next_year_index = False
            else:
                skip_next_year_index = True
            i += 1
            continue

        if skip_next_year_index:
            skip_next_year_index = False
            i += 1
            continue

        out.append(line)
        i += 1

    output_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _materialize_single_ofe_management_template(self, *, traffic: str) -> Path:
    source_path = self._resolve_legacy_management_template_path(traffic=traffic)
    output_path = Path(self.roads_runs_dir) / f"{source_path.stem}.single_ofe.man"
    self._build_single_ofe_management_file(template_path=source_path, output_path=output_path)
    return output_path

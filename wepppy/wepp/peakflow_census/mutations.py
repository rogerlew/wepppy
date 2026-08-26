"""Faithful Ksat and paired-cover mutation adapters."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .common import sha256_file


@dataclass(frozen=True)
class MutationRealization:
    file: str
    parameter: str
    requested_change: float
    source_value: Any
    expected_value: Any
    realized_value: Any
    lines: tuple[int, ...]
    tokens: tuple[int, ...]
    before_sha256: str
    after_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def soil_fields(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    try:
        marker = lines.index("Any comments:")
    except ValueError as error:
        raise ValueError(f"soil comments marker not found in {path}") from error
    for index, line in enumerate(lines[marker + 1 :], start=marker + 1):
        tokens = line.split()
        if len(tokens) < 10:
            continue
        try:
            [float(value) for value in tokens]
        except ValueError:
            continue
        return {"surface_ksat_mm_h": float(tokens[2]), "first_horizon_line": index}
    raise ValueError(f"no soil horizons in {path}")


def cover_fields(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    try:
        marker = next(index for index, line in enumerate(lines) if "Initial Condition Section" in line)
    except StopIteration as error:
        raise ValueError(f"initial cover section not found in {path}") from error
    for index, line in enumerate(lines[marker + 1 :], start=marker + 1):
        tokens = line.split()
        if len(tokens) != 6:
            continue
        try:
            values = [float(value) for value in tokens]
            rill_index = index + 3
            rill_values = [float(value) for value in lines[rill_index].split()]
        except (ValueError, IndexError):
            continue
        if 0 <= values[5] <= 1 and len(rill_values) == 5 and 0 <= rill_values[2] <= 1:
            return {"inrcov": values[5], "rilcov": rill_values[2], "inrcov_line": index, "rilcov_line": rill_index}
    raise ValueError(f"initial cover block not found in {path}")


def _replace_token(line: str, token_index: int, new_value: float) -> str:
    spans = list(re.finditer(r"\S+", line))
    if token_index >= len(spans):
        raise ValueError("mutation token index exceeds line token count")
    target = spans[token_index]
    return line[: target.start()] + f"{new_value:.15g}" + line[target.end() :]


def expected_mutation(path: Path, family: str, direction: str, change: float) -> dict[str, Any]:
    if direction not in {"minus", "plus"}:
        raise ValueError(f"unsupported direction: {direction}")
    if family == "ksat":
        fields = soil_fields(path)
        source = float(fields["surface_ksat_mm_h"])
        return {"parameter": "first_horizon_ksat_mm_h", "source_value": source,
                "expected_value": source * change, "lines": [fields["first_horizon_line"] + 1], "tokens": [3]}
    if family == "cover":
        fields = cover_fields(path)
        source = {"inrcov": float(fields["inrcov"]), "rilcov": float(fields["rilcov"])}
        expected = {key: value + change for key, value in source.items()}
        return {"parameter": "paired_inrcov_rilcov", "source_value": source,
                "expected_value": expected,
                "lines": [fields["inrcov_line"] + 1, fields["rilcov_line"] + 1], "tokens": [6, 3]}
    raise ValueError(f"unsupported mutation family: {family}")


def apply_mutation(trial: Any, run_dir: Path) -> MutationRealization:
    path = run_dir / trial.relative_input
    before_hash = sha256_file(path)
    expected = expected_mutation(path, trial.family, trial.direction, trial.requested_change)
    values = expected["expected_value"]
    if trial.family == "cover" and any(not 0 <= value <= 1 for value in values.values()):
        raise ValueError(f"cover mutation would clip for {trial.trial_id}")
    lines = path.read_text().splitlines(keepends=True)
    for line_number, token, value in zip(expected["lines"], expected["tokens"],
                                         [values] if isinstance(values, float) else values.values(), strict=True):
        index = line_number - 1
        ending = "\n" if lines[index].endswith("\n") else ""
        lines[index] = _replace_token(lines[index].rstrip("\n"), token - 1, float(value)) + ending
    path.write_text("".join(lines))
    reread = expected_mutation(path, trial.family, trial.direction, 1.0 if trial.family == "ksat" else 0.0)["source_value"]
    if isinstance(values, dict):
        if any(not math.isclose(float(reread[key]), float(value), rel_tol=1e-10) for key, value in values.items()):
            raise ValueError(f"cover mutation was erased for {trial.trial_id}")
    elif not math.isclose(float(reread), float(values), rel_tol=1e-10):
        raise ValueError(f"Ksat mutation was erased for {trial.trial_id}")
    after_hash = sha256_file(path)
    if before_hash == after_hash:
        raise ValueError(f"mutation did not change {path}")
    return MutationRealization(path.name, expected["parameter"], trial.requested_change,
                               expected["source_value"], values, reread,
                               tuple(expected["lines"]), tuple(expected["tokens"]), before_hash, after_hash)

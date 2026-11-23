"""Parsing and selection of generated Disturbed artifacts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from wepppy.wepp.management import Management

from .api_client import LiveAPIClient, LiveApiError


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _canonical_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(text)


def _artifact_text_hash(*, subpath: str, text: str) -> dict[str, Any]:
    payload = text.encode("utf-8")
    return {
        "subpath": subpath,
        "size_bytes": len(payload),
        "sha256": _sha256_bytes(payload),
    }


def _normalize_float_string(value: Any) -> str:
    text = str(value).strip()
    if text == "":
        return text
    try:
        return f"{float(text):.6f}"
    except ValueError:
        return text


def _parse_lookup_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]


def _lookup_key(row: dict[str, Any]) -> tuple[str, str]:
    luse = str(row.get("luse") or row.get("disturbed_class") or "").strip()
    stext = str(row.get("stext") or row.get("texid") or "").strip()
    return luse, stext


def _find_lookup_row_index(rows: list[dict[str, str]], *, luse: str, stext: str) -> int:
    target = (luse.strip(), stext.strip())
    for index, row in enumerate(rows):
        if _lookup_key(row) == target:
            return index
    raise LiveApiError(f"Target lookup row not found for key {target}")


def _apply_patch(
    rows: list[dict[str, str]],
    *,
    row_index: int,
    patch: dict[str, str],
) -> list[dict[str, str]]:
    out = [dict(row) for row in rows]
    for key, value in patch.items():
        if key not in out[row_index]:
            raise LiveApiError(f"Cannot patch missing column '{key}' in lookup row")
        out[row_index][key] = str(value)
    return out


def _parse_pmetpara(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise LiveApiError("pmetpara.txt was empty")
    records: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [part.strip() for part in line.split(",", 4)]
        if len(parts) != 5:
            continue
        records.append(
            {
                "plant": parts[0],
                "kcb": parts[1],
                "rawp": parts[2],
                "index": parts[3],
                "description": parts[4],
            }
        )
    return records


def _parse_sol_replacements(sol_text: str) -> dict[str, str]:
    replacements: dict[str, str] = {}
    in_block = False
    for raw_line in sol_text.splitlines():
        line = raw_line.strip()
        if line.startswith("# Replacements"):
            in_block = True
            continue
        if not in_block:
            continue
        if not line.startswith("#"):
            break
        body = line[1:].strip()
        if "->" not in body:
            continue
        key, value = body.split("->", 1)
        replacements[key.strip()] = value.strip()
    if not replacements:
        raise LiveApiError("Could not parse replacement block from .sol artifact")
    return replacements


def _parse_management_fields(man_text: str, *, management_fields: Iterable[str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="disturbed-live-e2e-man-") as tmpdir:
        tmp_path = Path(tmpdir) / "probe.man"
        tmp_path.write_text(man_text)
        management = Management.load(
            key=None,
            man_fn=tmp_path.name,
            man_dir=tmpdir,
            desc="disturbed-live-e2e",
        )

    if not management.plants or not management.inis:
        raise LiveApiError("Management file parse did not expose plant/ini sections")

    out: dict[str, str] = {}
    for field in management_fields:
        if field.startswith("plant.data."):
            attr = field[len("plant.data.") :]
            value = getattr(management.plants[0].data, attr)
            out[field] = _normalize_float_string(value)
        elif field.startswith("ini.data."):
            attr = field[len("ini.data.") :]
            value = getattr(management.inis[0].data, attr)
            out[field] = _normalize_float_string(value)
        else:
            raise LiveApiError(f"Unsupported management field selector: {field}")
    return out


def _select_property_sol_subpaths(
    client: LiveAPIClient,
    *,
    runid: str,
    config: str,
    bearer_token: str,
    target_luse: str,
    target_stext: str,
    management_fields: list[str],
) -> dict[str, Any]:
    pmetpara_text = client.download_text(
        runid=runid,
        config=config,
        subpath="wepp/runs/pmetpara.txt",
        bearer_token=bearer_token,
    )
    pmet_rows = _parse_pmetpara(pmetpara_text)

    target_entry: dict[str, Any] | None = None
    control_entry: dict[str, Any] | None = None

    for row in pmet_rows:
        index = row.get("index")
        if not index or not str(index).isdigit():
            continue
        sol_subpath = f"wepp/runs/p{index}.sol"
        try:
            sol_text = client.download_text(
                runid=runid,
                config=config,
                subpath=sol_subpath,
                bearer_token=bearer_token,
            )
        except LiveApiError:
            continue

        replacements = _parse_sol_replacements(sol_text)
        key = (
            str(replacements.get("luse") or "").strip(),
            str(replacements.get("stext") or "").strip(),
        )
        entry = {
            "index": index,
            "sol_subpath": sol_subpath,
            "sol_replacements": replacements,
            "key": {"luse": key[0], "stext": key[1]},
        }

        if key == (target_luse, target_stext):
            man_subpath = f"wepp/runs/p{index}.man"
            try:
                man_text = client.download_text(
                    runid=runid,
                    config=config,
                    subpath=man_subpath,
                    bearer_token=bearer_token,
                )
                man_fields = _parse_management_fields(man_text, management_fields=management_fields)
                entry["man_subpath"] = man_subpath
                entry["man_fields"] = man_fields
                target_entry = entry
                if control_entry is not None:
                    break
            except LiveApiError:
                continue
        else:
            if control_entry is None:
                control_entry = entry
            if target_entry is not None:
                break

    if target_entry is None:
        raise LiveApiError(
            f"Could not locate target property resource for lookup key ({target_luse}, {target_stext})"
        )
    if control_entry is None:
        raise LiveApiError("Could not locate non-target control property resource for scope assertion")

    return {
        "target": target_entry,
        "control": control_entry,
        "pmetpara_rows": pmet_rows,
    }

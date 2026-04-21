"""Milestone 2 seeded soil/landuse generators with soft invariant reporting."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

from wepppy.wepp.management.managements import get_management, load_map, read_management
from wepppy.wepp.soils.utils import SoilMultipleOfeSynth, WeppSoilUtil

SUPPORTED_EXTENSIONS: tuple[str, ...] = ("sol", "man", "slp", "cli")
DEFAULT_GENERATOR_SEED = 20260421


@dataclass(frozen=True, slots=True)
class SeedTuple:
    """Seed tuple assembled from a real ``/wc1/runs/**/wepp/runs`` directory."""

    seed_id: str
    run_id: str
    runs_dir: str
    stem: str
    sol_path: str
    man_path: str
    slp_path: str
    cli_path: str
    run_path: str | None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return asdict(self)


class StructuralContractError(RuntimeError):
    """Raised when structural/parser-validity contracts are violated."""


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seed_id(run_id: str, stem: str) -> str:
    digest = hashlib.sha1(f"{run_id}:{stem}".encode("utf-8")).hexdigest()[:12]
    return f"seed-{digest}"


def _mutation_seed(global_seed: int, case_index: int, seed_id: str) -> int:
    digest = hashlib.sha1(
        f"{global_seed}:{case_index}:{seed_id}".encode("utf-8")
    ).hexdigest()[:16]
    return int(digest, 16)


def discover_seed_tuples(
    run_root: str | Path = "/wc1/runs",
    *,
    max_run_dirs: int | None = None,
) -> list[SeedTuple]:
    """Discover structural seed tuples that contain ``.sol/.man/.slp/.cli``."""

    root = Path(run_root)
    if not root.exists():
        raise FileNotFoundError(f"Run root not found: {root}")

    run_dirs = sorted(path for path in root.glob("*/*/wepp/runs") if path.is_dir())
    if max_run_dirs is not None:
        if max_run_dirs <= 0:
            raise ValueError("max_run_dirs must be > 0 when provided.")
        run_dirs = run_dirs[:max_run_dirs]

    discovered: list[SeedTuple] = []
    for runs_dir in run_dirs:
        stems_by_ext: dict[str, set[str]] = {ext: set() for ext in SUPPORTED_EXTENSIONS}
        for path in runs_dir.iterdir():
            if not path.is_file():
                continue
            suffix = path.suffix.lower().lstrip(".")
            if suffix in stems_by_ext:
                stems_by_ext[suffix].add(path.stem)

        shared_stems = set(stems_by_ext["sol"])
        for ext in ("man", "slp", "cli"):
            shared_stems &= stems_by_ext[ext]

        rel_parts = runs_dir.relative_to(root).parts
        run_id = "/".join(rel_parts[:2])

        for stem in sorted(shared_stems):
            run_path = runs_dir / f"{stem}.run"
            discovered.append(
                SeedTuple(
                    seed_id=_seed_id(run_id=run_id, stem=stem),
                    run_id=run_id,
                    runs_dir=str(runs_dir),
                    stem=stem,
                    sol_path=str(runs_dir / f"{stem}.sol"),
                    man_path=str(runs_dir / f"{stem}.man"),
                    slp_path=str(runs_dir / f"{stem}.slp"),
                    cli_path=str(runs_dir / f"{stem}.cli"),
                    run_path=str(run_path) if run_path.exists() else None,
                )
            )

    return discovered


def summarize_seed_inventory(seed_tuples: Sequence[SeedTuple]) -> dict[str, Any]:
    """Build inventory metrics for docs/evidence artifacts."""

    by_run: dict[str, int] = {}
    by_bucket: dict[str, int] = {}

    for seed in seed_tuples:
        by_run[seed.run_id] = by_run.get(seed.run_id, 0) + 1
        bucket = seed.run_id.split("/", 1)[0]
        by_bucket[bucket] = by_bucket.get(bucket, 0) + 1

    run_counts = sorted(by_run.values())
    run_count_stats = {
        "min": run_counts[0] if run_counts else 0,
        "median": int(median(run_counts)) if run_counts else 0,
        "max": run_counts[-1] if run_counts else 0,
    }

    return {
        "total_seed_tuples": len(seed_tuples),
        "unique_runs": len(by_run),
        "bucket_counts": dict(sorted(by_bucket.items())),
        "stems_per_run": run_count_stats,
    }


def sample_seed_tuples(
    seed_tuples: Sequence[SeedTuple],
    *,
    sample_size: int,
    random_seed: int = DEFAULT_GENERATOR_SEED,
    per_run_cap: int = 3,
) -> list[SeedTuple]:
    """Deterministically sample seeds with run/bucket diversity preference."""

    if sample_size <= 0:
        raise ValueError("sample_size must be > 0")
    if per_run_cap <= 0:
        raise ValueError("per_run_cap must be > 0")

    rng = random.Random(random_seed)

    by_run: dict[str, list[SeedTuple]] = {}
    for seed in sorted(seed_tuples, key=lambda item: (item.run_id, item.stem)):
        by_run.setdefault(seed.run_id, []).append(seed)

    max_sampleable = sum(min(len(values), per_run_cap) for values in by_run.values())
    if sample_size > max_sampleable:
        raise ValueError(
            "sample_size exceeds available run-capped sample space "
            f"({sample_size=} > {max_sampleable=})."
        )

    capped_pool: list[SeedTuple] = []
    for run_id in sorted(by_run):
        candidates = list(by_run[run_id])
        rng.shuffle(candidates)
        capped_pool.extend(candidates[:per_run_cap])

    by_bucket: dict[str, list[SeedTuple]] = {}
    for seed in capped_pool:
        bucket = seed.run_id.split("/", 1)[0]
        by_bucket.setdefault(bucket, []).append(seed)

    for bucket in by_bucket:
        by_bucket[bucket] = sorted(by_bucket[bucket], key=lambda item: item.seed_id)
        rng.shuffle(by_bucket[bucket])

    bucket_names = sorted(by_bucket)
    rng.shuffle(bucket_names)
    sampled: list[SeedTuple] = []

    while bucket_names and len(sampled) < sample_size:
        next_round: list[str] = []
        for bucket in bucket_names:
            items = by_bucket[bucket]
            if not items:
                continue
            sampled.append(items.pop())
            if len(sampled) >= sample_size:
                break
            if items:
                next_round.append(bucket)
        bucket_names = next_round

    return sampled


def _existing_generated_paths(case_dir: Path, stem: str) -> dict[str, str | None]:
    """Return generated-path metadata using only files that currently exist."""
    generated_paths: dict[str, str | None] = {}
    for ext in ("sol", "man", "slp", "cli", "run"):
        candidate = case_dir / f"{stem}.{ext}"
        generated_paths[ext] = str(candidate) if candidate.exists() else None
    return generated_paths


def _mutate_soil(soil_util: WeppSoilUtil, rng: random.Random) -> list[dict[str, Any]]:
    mutations: list[dict[str, Any]] = []
    for ofe_idx, ofe in enumerate(soil_util.obj.get("ofes", [])):
        sat_value = _to_float(ofe.get("sat"))
        if sat_value is not None:
            sat_multiplier = rng.uniform(0.35, 1.9)
            ofe["sat"] = round(sat_value * sat_multiplier, 6)
            mutations.append(
                {
                    "target": f"ofe[{ofe_idx}].sat",
                    "mode": "multiply",
                    "multiplier": round(sat_multiplier, 6),
                    "value": ofe["sat"],
                }
            )

        for horizon_idx, horizon in enumerate(ofe.get("horizons", [])):
            for key, lo, hi in (
                ("bd", 0.7, 1.35),
                ("ksat", 0.1, 2.3),
                ("fc", 0.55, 1.6),
                ("wp", 0.55, 1.85),
                ("orgmat", 0.25, 2.4),
                ("rfg", 0.5, 2.0),
            ):
                current = _to_float(horizon.get(key))
                if current is None:
                    continue
                multiplier = rng.uniform(lo, hi)
                horizon[key] = round(current * multiplier, 6)
                mutations.append(
                    {
                        "target": f"ofe[{ofe_idx}].horizons[{horizon_idx}].{key}",
                        "mode": "multiply",
                        "multiplier": round(multiplier, 6),
                        "value": horizon[key],
                    }
                )

            for key in ("sand", "clay"):
                current = _to_float(horizon.get(key))
                if current is None:
                    continue
                delta = rng.uniform(-18.0, 18.0)
                horizon[key] = round(current + delta, 6)
                mutations.append(
                    {
                        "target": f"ofe[{ofe_idx}].horizons[{horizon_idx}].{key}",
                        "mode": "add",
                        "delta": round(delta, 6),
                        "value": horizon[key],
                    }
                )

    return mutations


def _set_management_override(
    management: Any, attr: str, value: float
) -> dict[str, Any] | None:
    try:
        management[attr] = value
    except (AttributeError, NotImplementedError, ValueError):
        return None

    return {"target": attr, "value": value}


def _mutate_management(
    management: Any, rng: random.Random
) -> list[dict[str, Any]]:
    mutations: list[dict[str, Any]] = []
    candidates = [
        ("ini.data.cancov", round(rng.uniform(-0.2, 1.35), 6)),
        ("ini.data.inrcov", round(rng.uniform(-0.2, 1.35), 6)),
        ("ini.data.rilcov", round(rng.uniform(-0.2, 1.35), 6)),
        ("plant.data.rdmax", round(rng.uniform(-0.25, 4.5), 6)),
        ("plant.data.xmxlai", round(rng.uniform(-0.5, 12.0), 6)),
    ]

    for attr, value in candidates:
        result = _set_management_override(management, attr, value)
        if result is not None:
            mutations.append(result)

    return mutations


def evaluate_soft_invariants(soil_util: WeppSoilUtil, management: Any) -> list[dict[str, Any]]:
    """Evaluate advisory-only physical plausibility checks."""

    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, message: str, value: Any) -> None:
        checks.append(
            {
                "name": name,
                "severity": "info" if ok else "warn",
                "outcome": "pass" if ok else "warn",
                "message": message,
                "value": value,
            }
        )

    for ofe_idx, ofe in enumerate(soil_util.obj.get("ofes", [])):
        sat_value = _to_float(ofe.get("sat"))
        if sat_value is not None:
            add_check(
                f"soil.ofe[{ofe_idx}].sat_range",
                0.0 <= sat_value <= 1.0,
                "Expected saturation between 0 and 1 for typical physical states.",
                sat_value,
            )

        for horizon_idx, horizon in enumerate(ofe.get("horizons", [])):
            sand = _to_float(horizon.get("sand"))
            clay = _to_float(horizon.get("clay"))
            bd = _to_float(horizon.get("bd"))
            ksat = _to_float(horizon.get("ksat"))
            wp = _to_float(horizon.get("wp"))
            fc = _to_float(horizon.get("fc"))

            if sand is not None and clay is not None:
                texture_sum = sand + clay
                add_check(
                    f"soil.ofe[{ofe_idx}].horizons[{horizon_idx}].texture_sum",
                    0.0 <= texture_sum <= 100.0,
                    "Expected sand + clay within [0, 100].",
                    round(texture_sum, 6),
                )

            if bd is not None:
                add_check(
                    f"soil.ofe[{ofe_idx}].horizons[{horizon_idx}].bd_range",
                    0.6 <= bd <= 2.2,
                    "Expected bulk density in [0.6, 2.2] g/cm^3.",
                    bd,
                )

            if ksat is not None:
                add_check(
                    f"soil.ofe[{ofe_idx}].horizons[{horizon_idx}].ksat_positive",
                    ksat > 0.0,
                    "Expected ksat > 0.",
                    ksat,
                )

            if wp is not None and fc is not None:
                add_check(
                    f"soil.ofe[{ofe_idx}].horizons[{horizon_idx}].wp_lte_fc",
                    wp <= fc,
                    "Expected wilting point <= field capacity.",
                    {"wp": wp, "fc": fc},
                )

    for idx, ini_loop in enumerate(getattr(management, "inis", [])):
        data = getattr(ini_loop, "data", None)
        if data is None:
            continue
        for attr in ("cancov", "inrcov", "rilcov"):
            value = _to_float(getattr(data, attr, None))
            if value is None:
                continue
            add_check(
                f"management.ini[{idx}].{attr}_range",
                0.0 <= value <= 1.0,
                f"Expected {attr} in [0, 1].",
                value,
            )

    for idx, plant_loop in enumerate(getattr(management, "plants", [])):
        data = getattr(plant_loop, "data", None)
        if data is None:
            continue

        rdmax = _to_float(getattr(data, "rdmax", None))
        if rdmax is not None:
            add_check(
                f"management.plant[{idx}].rdmax_positive",
                rdmax > 0.0,
                "Expected rdmax > 0.",
                rdmax,
            )

        xmxlai = _to_float(getattr(data, "xmxlai", None))
        if xmxlai is not None:
            add_check(
                f"management.plant[{idx}].xmxlai_nonnegative",
                xmxlai >= 0.0,
                "Expected xmxlai >= 0.",
                xmxlai,
            )

    return checks


class SeededSoilLanduseGenerator:
    """Seed-first soil/landuse generator for Milestone 2 pilot workflows."""

    def __init__(
        self,
        *,
        run_root: str | Path = "/wc1/runs",
        random_seed: int = DEFAULT_GENERATOR_SEED,
        catalog_map: str | None = None,
    ) -> None:
        self.run_root = Path(run_root)
        self.random_seed = random_seed
        self.catalog_map = catalog_map
        map_payload = load_map(_map=catalog_map)
        self._catalog_keys = sorted(int(key) for key in map_payload.keys())

    def discover(self, *, max_run_dirs: int | None = None) -> list[SeedTuple]:
        return discover_seed_tuples(self.run_root, max_run_dirs=max_run_dirs)

    def _choose_management_source(
        self,
        *,
        seed: SeedTuple,
        rng: random.Random,
    ) -> tuple[Any, dict[str, Any]]:
        if self._catalog_keys and rng.random() < 0.35:
            key = rng.choice(self._catalog_keys)
            management = get_management(key, _map=self.catalog_map)
            return management, {
                "source": "catalog",
                "catalog_key": key,
                "catalog_map": self.catalog_map,
                "catalog_man_fn": management.man_fn,
            }

        return read_management(seed.man_path), {
            "source": "seed",
            "seed_man_path": seed.man_path,
        }

    def _write_mutated_soil(
        self,
        *,
        seed: SeedTuple,
        rng: random.Random,
        output_sol_path: Path,
    ) -> tuple[WeppSoilUtil, list[dict[str, Any]]]:
        soil_util = WeppSoilUtil(seed.sol_path)
        soil_mutations = _mutate_soil(soil_util, rng)

        ntemp = int(soil_util.obj.get("ntemp", 1))
        if ntemp <= 1:
            staging_dir = Path(tempfile.mkdtemp(prefix="m2_soil_stage_"))
            try:
                staged_single = staging_dir / f"{seed.stem}.sol"
                soil_util.write(str(staged_single))
                synth = SoilMultipleOfeSynth([str(staged_single)])
                ksflag = int(soil_util.obj.get("ksflag", 0))
                synth.write(str(output_sol_path), ksflag=ksflag)
            finally:
                shutil.rmtree(staging_dir, ignore_errors=True)
        else:
            # Preserve existing multi-OFE structure; single-file synth can clobber ntemp.
            soil_util.write(str(output_sol_path))

        # Structural contract check: generated soil must parse.
        parsed_generated_soil = WeppSoilUtil(str(output_sol_path))
        return parsed_generated_soil, soil_mutations

    def generate_case(
        self,
        *,
        seed: SeedTuple,
        case_index: int,
        output_root: str | Path,
    ) -> dict[str, Any]:
        """Generate one case with structural hard-fails and soft invariant metadata."""

        for required in (seed.sol_path, seed.man_path, seed.slp_path, seed.cli_path):
            if not Path(required).exists():
                raise StructuralContractError(
                    f"Seed tuple is missing required input file: {required}"
                )

        case_id = f"m2-case-{case_index:04d}-{seed.seed_id}"
        mutation_seed = _mutation_seed(self.random_seed, case_index, seed.seed_id)
        rng = random.Random(mutation_seed)

        case_dir = Path(output_root) / case_id
        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True, exist_ok=False)

        generated_sol = case_dir / f"{seed.stem}.sol"
        generated_man = case_dir / f"{seed.stem}.man"
        generated_slp = case_dir / f"{seed.stem}.slp"
        generated_cli = case_dir / f"{seed.stem}.cli"
        generated_run = case_dir / f"{seed.stem}.run"

        parsed_generated_soil, soil_mutations = self._write_mutated_soil(
            seed=seed, rng=rng, output_sol_path=generated_sol
        )

        management, management_source = self._choose_management_source(seed=seed, rng=rng)
        management_mutations = _mutate_management(management, rng)
        try:
            with generated_man.open("w", encoding="utf-8") as handle:
                handle.write(str(management))
            # Structural contract check: generated management must parse.
            parsed_generated_management = read_management(str(generated_man))
        except Exception as exc:
            if management_source.get("source") != "catalog":
                raise

            fallback_management = read_management(seed.man_path)
            management_mutations = _mutate_management(fallback_management, rng)
            management_source = {
                "source": "seed_fallback_after_catalog_parse_failure",
                "seed_man_path": seed.man_path,
                "catalog_key": management_source.get("catalog_key"),
                "catalog_map": management_source.get("catalog_map"),
                "fallback_reason": str(exc),
            }
            with generated_man.open("w", encoding="utf-8") as handle:
                handle.write(str(fallback_management))
            parsed_generated_management = read_management(str(generated_man))

        shutil.copy2(seed.slp_path, generated_slp)
        shutil.copy2(seed.cli_path, generated_cli)
        if seed.run_path is not None and Path(seed.run_path).exists():
            shutil.copy2(seed.run_path, generated_run)
        else:
            generated_run = None

        soft_invariants = evaluate_soft_invariants(
            parsed_generated_soil, parsed_generated_management
        )
        soft_warning_count = sum(
            1 for check in soft_invariants if check["outcome"] == "warn"
        )

        metadata: dict[str, Any] = {
            "case_id": case_id,
            "status": "ok",
            "seed_id": seed.seed_id,
            "seed_lineage": seed.as_dict(),
            "mutation_seed": mutation_seed,
            "lineage": {
                "soil_mutations": soil_mutations,
                "management_source": management_source,
                "management_mutations": management_mutations,
                "slope_climate_policy": "borrowed_from_seed_context",
            },
            "hard_failures": [],
            "soft_invariants": soft_invariants,
            "soft_warning_count": soft_warning_count,
            "generated_paths": {
                "sol": str(generated_sol),
                "man": str(generated_man),
                "slp": str(generated_slp),
                "cli": str(generated_cli),
                "run": str(generated_run) if generated_run else None,
            },
        }

        metadata_path = case_dir / "case_metadata.json"
        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)

        return metadata

    def generate_batch(
        self,
        *,
        seeds: Sequence[SeedTuple],
        output_root: str | Path,
    ) -> dict[str, Any]:
        """Generate a reproducible case batch and write manifest artifacts."""

        output_dir = Path(output_root)
        output_dir.mkdir(parents=True, exist_ok=True)

        case_metadata: list[dict[str, Any]] = []
        for index, seed in enumerate(seeds, start=1):
            try:
                metadata = self.generate_case(
                    seed=seed, case_index=index, output_root=output_dir
                )
            # Deliberate boundary: upstream parser/writer APIs raise heterogeneous exceptions.
            except Exception as exc:
                case_id = f"m2-case-{index:04d}-{seed.seed_id}"
                case_dir = output_dir / case_id
                case_dir.mkdir(parents=True, exist_ok=True)
                metadata = {
                    "case_id": case_id,
                    "status": "hard_fail",
                    "seed_id": seed.seed_id,
                    "seed_lineage": seed.as_dict(),
                    "mutation_seed": _mutation_seed(self.random_seed, index, seed.seed_id),
                    "hard_failures": [str(exc)],
                    "soft_invariants": [],
                    "soft_warning_count": 0,
                    "generated_paths": _existing_generated_paths(case_dir, seed.stem),
                }
                with (case_dir / "case_metadata.json").open("w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, indent=2, sort_keys=True)
            case_metadata.append(metadata)

        manifest = {
            "generator_seed": self.random_seed,
            "total_cases": len(case_metadata),
            "ok_cases": sum(1 for case in case_metadata if case["status"] == "ok"),
            "hard_fail_cases": sum(
                1 for case in case_metadata if case["status"] == "hard_fail"
            ),
            "cases": case_metadata,
        }

        manifest_json = output_dir / "pilot_manifest.json"
        with manifest_json.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)

        manifest_csv = output_dir / "pilot_manifest.csv"
        with manifest_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "case_id",
                    "status",
                    "seed_id",
                    "mutation_seed",
                    "soft_warning_count",
                    "hard_failure_count",
                    "sol_path",
                    "man_path",
                    "slp_path",
                    "cli_path",
                    "run_path",
                ],
            )
            writer.writeheader()
            for case in case_metadata:
                generated_paths = case.get("generated_paths", {})
                writer.writerow(
                    {
                        "case_id": case["case_id"],
                        "status": case["status"],
                        "seed_id": case["seed_id"],
                        "mutation_seed": case["mutation_seed"],
                        "soft_warning_count": case.get("soft_warning_count", 0),
                        "hard_failure_count": len(case.get("hard_failures", [])),
                        "sol_path": generated_paths.get("sol"),
                        "man_path": generated_paths.get("man"),
                        "slp_path": generated_paths.get("slp"),
                        "cli_path": generated_paths.get("cli"),
                        "run_path": generated_paths.get("run"),
                    }
                )

        manifest["manifest_json"] = str(manifest_json)
        manifest["manifest_csv"] = str(manifest_csv)
        return manifest


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Milestone 2 seeded soil/landuse pilot cases from "
            "/wc1/runs/**/wepp/runs seed tuples."
        )
    )
    parser.add_argument("--run-root", default="/wc1/runs")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--sample-size", type=int, default=12)
    parser.add_argument("--seed", type=int, default=DEFAULT_GENERATOR_SEED)
    parser.add_argument("--per-run-cap", type=int, default=3)
    parser.add_argument("--catalog-map", default=None)
    parser.add_argument("--max-run-dirs", type=int, default=None)
    parser.add_argument("--inventory-json", default=None)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_cli()
    args = parser.parse_args(list(argv) if argv is not None else None)

    generator = SeededSoilLanduseGenerator(
        run_root=args.run_root, random_seed=args.seed, catalog_map=args.catalog_map
    )
    discovered = generator.discover(max_run_dirs=args.max_run_dirs)
    if not discovered:
        raise RuntimeError("No seed tuples discovered.")

    sampled = sample_seed_tuples(
        discovered,
        sample_size=args.sample_size,
        random_seed=args.seed,
        per_run_cap=args.per_run_cap,
    )
    manifest = generator.generate_batch(seeds=sampled, output_root=args.output_root)
    inventory = summarize_seed_inventory(discovered)

    payload = {
        "inventory": inventory,
        "sampling_policy": {
            "sample_size": args.sample_size,
            "per_run_cap": args.per_run_cap,
            "seed": args.seed,
            "strategy": (
                "deterministic run-capped sampling with bucket-level round-robin"
            ),
        },
        "sampled_seed_ids": [seed.seed_id for seed in sampled],
        "manifest": manifest,
    }

    if args.inventory_json:
        inventory_path = Path(args.inventory_json)
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        with inventory_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

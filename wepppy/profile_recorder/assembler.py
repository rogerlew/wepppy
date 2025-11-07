from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from wepppy.nodb import base as nodb_base

from .utils import sanitise_component

LOGGER = logging.getLogger(__name__)

TASK_RULES: Dict[str, Dict[str, Any]] = {
    "rq/api/fetch_dem_and_build_channels": {
        "expected_files": ["dem/dem.tif"],
        "ron_property": ("has_dem", {"equals": True}),
    },
    "rq/api/set_outlet": {
        "ron_property": ("watershed_instance.outlet", {"exists": True}),
    },
    "rq/api/build_subcatchments_and_abstract_watershed": {
        "expected_files": ["dem/channels.shp", "dem/subwta.shp"],
    },
    "rq/api/build_landuse": {
        "ron_property": ("landuse_instance.domlc_d", {"exists": True}),
    },
}


class ProfileAssembler:
    """
    Streaming assembler stub.

    Observes recorder events and mirrors them into the profile data repository.
    The initial implementation simply appends events to a draft log so that no
    information is lost before full assembly logic lands.
    """

    def __init__(self, data_repo_root: Path) -> None:
        self.data_repo_root = Path(data_repo_root)

    def handle_event(
        self,
        run_id: str,
        capture_id: Optional[str],
        event: Dict[str, Any],
        run_dir: Optional[Path],
        *,
        file_hints: Optional[Dict[str, Path]] = None,
    ) -> None:
        try:
            run_key = sanitise_component(run_id or "global")
            capture_key = sanitise_component(capture_id or "stream")
            draft_root = self.data_repo_root / "profiles" / "_drafts" / run_key / capture_key
            draft_root.mkdir(parents=True, exist_ok=True)

            events_path = draft_root / "events.jsonl"
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, separators=(",", ":")) + "\n")

            if run_dir:
                pointer_path = draft_root / "run_dir.txt"
                if not pointer_path.exists():
                    pointer_path.write_text(str(run_dir), encoding="utf-8")

            config_slug = self._extract_config_slug(event)
            if config_slug:
                self._ensure_config_seed(draft_root, config_slug, run_dir)

            stage = event.get("stage")
            if stage and stage.lower() != "response":
                return
            if event.get("ok") is False:
                return

            if stage == "response" and event.get("category") == "file_upload":
                self._capture_file_upload(event, draft_root, run_dir)

            if file_hints:
                seed_root = draft_root / "seed"
                seed_root.mkdir(parents=True, exist_ok=True)
                for label, candidate in file_hints.items():
                    self._snapshot_candidate(seed_root, label, candidate)

            endpoint = self._normalise_endpoint(event)
            if endpoint:
                rules = TASK_RULES.get(endpoint)
                if rules:
                    self._apply_task_rules(
                        draft_root,
                        run_id,
                        run_dir,
                        endpoint,
                        rules,
                    )
        except Exception as exc:
            LOGGER.debug("ProfileAssembler handle_event encountered an error: %s", exc)

    def promote_draft(
        self,
        run_id: str,
        capture_id: str = "stream",
        *,
        slug: Optional[str] = None,
    ) -> Dict[str, str]:
        run_key = sanitise_component(run_id or "global")
        capture_key = sanitise_component(capture_id or "stream")
        draft_root = self.data_repo_root / "profiles" / "_drafts" / run_key / capture_key
        if not draft_root.exists():
            raise FileNotFoundError(f"Draft not found for run '{run_id}' ({capture_id})")

        slug_key = sanitise_component(slug or run_id or "profile")
        profile_root = self.data_repo_root / "profiles" / slug_key
        capture_target = profile_root / "capture"
        capture_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(draft_root, capture_target, dirs_exist_ok=True)

        run_src = None
        run_pointer = draft_root / "run_dir.txt"
        if run_pointer.exists():
            run_src = Path(run_pointer.read_text().strip())
            if run_src.exists():
                shutil.copytree(run_src, profile_root / "run", dirs_exist_ok=True)

        return {
            "profile_root": str(profile_root),
            "capture_path": str(capture_target),
            "run_source": str(run_src) if run_src else "",
        }

    @staticmethod
    def _snapshot_candidate(seed_root: Path, label: str, candidate: Path) -> None:
        safe_label = sanitise_component(label)
        target = seed_root / safe_label

        try:
            if candidate.exists():
                if candidate.is_dir():
                    (target.with_suffix(".dir.exists")).touch(exist_ok=True)
                else:
                    target = target.with_suffix(candidate.suffix)
                    if not target.exists():
                        shutil.copy2(candidate, target)
            else:
                (seed_root / f"{safe_label}.missing").touch(exist_ok=True)
        except Exception as exc:
            LOGGER.debug("Failed to snapshot %s (%s): %s", label, candidate, exc)

    @staticmethod
    def _normalise_endpoint(event: Dict[str, Any]) -> Optional[str]:
        endpoint = event.get("endpoint")
        if not endpoint or not isinstance(endpoint, str):
            return None
        # If the endpoint contains a run-scoped prefix, strip it.
        parts = endpoint.split("/rq/", 1)
        if len(parts) == 2:
            return "rq/" + parts[1]
        # Fall back to stripping leading slash.
        return endpoint.lstrip("/")

    def _apply_task_rules(
        self,
        draft_root: Path,
        run_id: str,
        run_dir: Optional[Path],
        endpoint: str,
        rules: Dict[str, Any],
    ) -> None:
        notes = []

        expected_files = rules.get("expected_files", [])
        if run_dir and expected_files:
            seed_root = draft_root / "seed"
            seed_root.mkdir(parents=True, exist_ok=True)
            for rel_path in expected_files:
                candidate = run_dir / rel_path
                label = f"{endpoint}:{rel_path}"
                if candidate.exists():
                    self._snapshot_candidate(seed_root, label, candidate)
                else:
                    note = f"[files] missing {rel_path}"
                    notes.append(note)
                    self._snapshot_candidate(seed_root, label, candidate)

        ron_prop = rules.get("ron_property")
        if ron_prop:
            attr, expectation = ron_prop
            try:
                from wepppy.nodb.core.ron import Ron

                ron = Ron.getInstanceFromRunID(run_id, ignore_lock=True)
            except Exception as exc:
                notes.append(f"[ron] failed to read {attr}: {exc}")
            else:
                match = self._evaluate_ron_expectation(ron, attr, expectation)
                if match is not None:
                    notes.append(match)

        if notes:
            note_path = draft_root / "validation.log"
            with note_path.open("a", encoding="utf-8") as handle:
                for note in notes:
                    handle.write(f"{endpoint}: {note}\n")

    def _capture_file_upload(
        self,
        event: Dict[str, Any],
        draft_root: Path,
        run_dir: Optional[Path],
    ) -> None:
        if run_dir is None:
            return

        endpoint = self._normalise_endpoint(event) or ""
        seed_root = draft_root / "seed" / "uploads"
        seed_root.mkdir(parents=True, exist_ok=True)

        if endpoint == "rq/api/build_landuse":
            self._snapshot_landuse_upload(seed_root, Path(run_dir))
        elif endpoint.endswith("tasks/upload_sbs"):
            self._snapshot_sbs_upload(seed_root, Path(run_dir))
        elif endpoint.endswith("tasks/upload_cover_transform"):
            self._snapshot_cover_transform_upload(seed_root, Path(run_dir))
        elif endpoint.endswith("tasks/upload_cli"):
            self._snapshot_cli_upload(seed_root, Path(run_dir))
        elif endpoint == "rq/api/build_treatments":
            self._snapshot_landuse_upload(seed_root, Path(run_dir))
        elif endpoint == "rq/api/run_ash":
            self._snapshot_ash_upload(seed_root, Path(run_dir))
        elif endpoint == "rq/api/run_omni":
            self._snapshot_omni_upload(seed_root, Path(run_dir))

    def _snapshot_landuse_upload(self, seed_root: Path, run_dir: Path) -> None:
        try:
            from wepppy.nodb.core.landuse import Landuse
        except Exception as exc:
            LOGGER.debug("Landuse import failed while capturing upload: %s", exc)
            return

        try:
            landuse = Landuse.getInstance(str(run_dir))
        except Exception as exc:
            LOGGER.debug("Failed to instantiate Landuse for upload capture: %s", exc)
            return

        target_dir = seed_root / "landuse"
        target_dir.mkdir(parents=True, exist_ok=True)

        lc_fn = Path(landuse.lc_fn)
        if lc_fn.exists():
            self._copy_seed_file(lc_fn, target_dir / lc_fn.name)
            meta = Path(str(lc_fn) + ".meta")
            if meta.exists():
                self._copy_seed_file(meta, target_dir / meta.name)

            canonical = target_dir / f"input_upload_landuse{lc_fn.suffix}"
            if not canonical.exists():
                self._copy_seed_file(lc_fn, canonical)

    def _snapshot_sbs_upload(self, seed_root: Path, run_dir: Path) -> None:
        candidates: list[Path] = []

        try:
            from wepppy.nodb.mods.disturbed import Disturbed
            disturbed = Disturbed.getInstance(str(run_dir))
            disturbed_path = disturbed.disturbed_path
            if disturbed_path:
                path = Path(disturbed_path)
                if path.exists():
                    candidates.append(path)
        except Exception:
            pass

        try:
            from wepppy.nodb.mods.baer import Baer
            baer = Baer.getInstance(str(run_dir))
            baer_path = baer.baer_path
            if baer_path:
                path = Path(baer_path)
                if path.exists():
                    candidates.append(path)
        except Exception:
            pass

        search_roots = [run_dir / "disturbed", run_dir / "baer"]
        for root in search_roots:
            if root.is_dir():
                for candidate in root.glob("*.tif"):
                    if candidate not in candidates:
                        candidates.append(candidate)

        if not candidates:
            return

        target_dir = seed_root / "sbs"
        target_dir.mkdir(parents=True, exist_ok=True)
        for src in candidates:
            self._copy_seed_file(src, target_dir / src.name)

        canonical = target_dir / f"input_upload_sbs{candidates[0].suffix}"
        if not canonical.exists():
            self._copy_seed_file(candidates[0], canonical)

    def _snapshot_cover_transform_upload(self, seed_root: Path, run_dir: Path) -> None:
        try:
            from wepppy.nodb.mods.revegetation import Revegetation
        except Exception as exc:
            LOGGER.debug("Revegetation import failed while capturing upload: %s", exc)
            return

        try:
            reveg = Revegetation.getInstance(str(run_dir))
        except Exception as exc:
            LOGGER.debug("Failed to instantiate Revegetation for upload capture: %s", exc)
            return

        target_dir = seed_root / "revegetation"
        target_dir.mkdir(parents=True, exist_ok=True)

        path = Path(getattr(reveg, "cover_transform_path", ""))
        if path.exists():
            self._copy_seed_file(path, target_dir / path.name)
            canonical = target_dir / f"input_upload_cover_transform{path.suffix or '.csv'}"
            if not canonical.exists():
                self._copy_seed_file(path, canonical)

    def _snapshot_cli_upload(self, seed_root: Path, run_dir: Path) -> None:
        try:
            from wepppy.nodb.core.climate import Climate
        except Exception as exc:
            LOGGER.debug("Climate import failed while capturing CLI upload: %s", exc)
            return

        try:
            climate = Climate.getInstance(str(run_dir))
        except Exception as exc:
            LOGGER.debug("Failed to instantiate Climate for CLI capture: %s", exc)
            return

        cli_path = Path(climate.orig_cli_fn or "")
        if not cli_path.exists():
            cli_path = Path(climate.cli_dir) / Path(cli_path.name or "")
        if not cli_path.exists():
            return

        target_dir = seed_root / "climate"
        target_dir.mkdir(parents=True, exist_ok=True)
        self._copy_seed_file(cli_path, target_dir / cli_path.name)
        canonical = target_dir / f"input_upload_cli{cli_path.suffix or '.cli'}"
        if not canonical.exists():
            self._copy_seed_file(cli_path, canonical)

    def _snapshot_ash_upload(self, seed_root: Path, run_dir: Path) -> None:
        try:
            from wepppy.nodb.mods.ash_transport import Ash
        except Exception as exc:
            LOGGER.debug("Ash import failed while capturing ash upload: %s", exc)
            return

        try:
            ash = Ash.getInstance(str(run_dir))
        except Exception as exc:
            LOGGER.debug("Failed to instantiate Ash for upload capture: %s", exc)
            return

        target_dir = seed_root / "ash"
        target_dir.mkdir(parents=True, exist_ok=True)

        load_path = getattr(ash, "ash_load_fn", None)
        if load_path:
            load_path = Path(load_path)
            if load_path.exists():
                self._copy_seed_file(load_path, target_dir / load_path.name)
                canonical = target_dir / f"input_upload_ash_load{load_path.suffix or '.tif'}"
                if not canonical.exists():
                    self._copy_seed_file(load_path, canonical)

        type_path = getattr(ash, "ash_type_map_fn", None)
        if type_path:
            type_path = Path(type_path)
            if type_path.exists():
                self._copy_seed_file(type_path, target_dir / type_path.name)
                canonical_type = target_dir / f"input_upload_ash_type_map{type_path.suffix or '.tif'}"
                if not canonical_type.exists():
                    self._copy_seed_file(type_path, canonical_type)

    def _snapshot_omni_upload(self, seed_root: Path, run_dir: Path) -> None:
        omni_seed = seed_root / "omni"
        omni_seed.mkdir(parents=True, exist_ok=True)

        limbo_src = run_dir / "omni" / "_limbo"
        if limbo_src.exists():
            limbo_dest = omni_seed / "_limbo"
            try:
                shutil.copytree(limbo_src, limbo_dest, dirs_exist_ok=True)
            except Exception as exc:
                LOGGER.debug("Failed to copy omni limbo directory: %s", exc)

    @staticmethod
    def _copy_seed_file(source: Path, target: Path) -> None:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                shutil.copy2(source, target)
        except Exception as exc:
            LOGGER.debug("Failed to copy seed file %s -> %s: %s", source, target, exc)

    @staticmethod
    def _extract_config_slug(event: Dict[str, Any]) -> Optional[str]:
        slug_from_meta = ProfileAssembler._normalise_config_slug(event.get("config"))
        if slug_from_meta:
            return slug_from_meta

        endpoint = event.get("endpoint")
        if not endpoint or not isinstance(endpoint, str):
            return None
        path = urlparse(endpoint).path or endpoint
        segments = [part for part in path.split("/") if part]
        if "runs" not in segments:
            return None
        try:
            idx = segments.index("runs")
            return ProfileAssembler._normalise_config_slug(segments[idx + 2])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _normalise_config_slug(raw_slug: Optional[str]) -> Optional[str]:
        if not isinstance(raw_slug, str):
            return None
        slug = raw_slug.strip()
        if not slug:
            return None
        if slug.endswith(".cfg"):
            slug = slug[:-4]
        return slug or None

    def _ensure_config_seed(
        self,
        draft_root: Path,
        config_slug: str,
        run_dir: Optional[Path],
    ) -> None:
        config_dir = draft_root / "seed" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            config_slug if config_slug.endswith(".cfg") else f"{config_slug}.cfg"
        )

        target_cfg = config_dir / filename
        if not target_cfg.exists():
            candidates = []
            if run_dir is not None:
                candidates.append(run_dir / filename)
            candidates.append(Path(nodb_base.get_config_dir()) / filename)

            for candidate in candidates:
                if candidate.exists():
                    try:
                        shutil.copy2(candidate, target_cfg)
                    except Exception as exc:
                        LOGGER.debug(
                            "Failed to copy config seed %s from %s: %s",
                            filename,
                            candidate,
                            exc,
                        )
                    break

        active_path = config_dir / "active_config.txt"
        try:
            active_path.write_text(config_slug, encoding="utf-8")
        except Exception as exc:
            LOGGER.debug("Failed to write active config seed %s: %s", config_slug, exc)

        defaults_target = config_dir / Path(nodb_base.get_default_config_path()).name
        if not defaults_target.exists():
            defaults_source = Path(nodb_base.get_default_config_path())
            if defaults_source.exists():
                try:
                    shutil.copy2(defaults_source, defaults_target)
                except Exception as exc:
                    LOGGER.debug(
                        "Failed to copy default config seed from %s: %s",
                        defaults_source,
                        exc,
                    )

    @staticmethod
    def _evaluate_ron_expectation(ron: Any, attr: str, expectation: Dict[str, Any]) -> Optional[str]:
        if ron is None:
            return f"[ron] {attr} unavailable"

        current = ron
        for token in attr.split("."):
            if not token:
                continue
            current = getattr(current, token, None)

        if "equals" in expectation:
            expected_value = expectation["equals"]
            if current != expected_value:
                return f"[ron] {attr} expected {expected_value!r}, got {current!r}"
            return None

        if expectation.get("exists"):
            if current in (None, False, {}, [], ""):
                return f"[ron] {attr} missing or empty"
            return None

        return None

        if notes:
            note_path = draft_root / "validation.log"
            with note_path.open("a", encoding="utf-8") as handle:
                for note in notes:
                    handle.write(f"{endpoint}: {note}\n")

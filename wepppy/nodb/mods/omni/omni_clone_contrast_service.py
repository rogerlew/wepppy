from __future__ import annotations

import errno
import json
import os
import shutil
import time
from os.path import exists as _exists
from os.path import isfile as _isfile
from os.path import join as _join
from os.path import split as _split
from pathlib import Path
from typing import Any, Dict, Optional


def _rmtree_with_retry(
    path: str | Path,
    *,
    retries: int = 3,
    delay_seconds: float = 0.25,
) -> None:
    path_obj = Path(path)
    for attempt in range(1, max(1, retries) + 1):
        try:
            shutil.rmtree(path_obj)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            retryable = exc.errno in {errno.ENOTEMPTY, errno.EBUSY}
            if not retryable or attempt >= retries:
                raise
            time.sleep(delay_seconds * attempt)


def _reset_workspace(path: str | Path, *, logger: Any) -> None:
    target = Path(path)
    if not target.exists():
        return

    stale_dir = target.with_name(
        f"{target.name}.stale.{int(time.time() * 1000)}.{os.getpid()}"
    )
    try:
        os.replace(target, stale_dir)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RuntimeError(
            f"omni clone workspace reset rename failed for {target}: {exc}"
        ) from exc

    try:
        _rmtree_with_retry(stale_dir)
    except OSError as exc:
        # Boundary catch: stale workspace cleanup should not fail clone startup.
        logger.warning(
            "omni clone workspace reset: deferred cleanup failed for %s (%s); leaving stale dir in place",
            stale_dir,
            exc,
        )


class OmniCloneContrastService:
    """Own heavy clone/contrast internals while preserving module-level seams."""

    @staticmethod
    def _run_contrast_contract_refs():
        from wepppy.nodb.mods.omni.omni import (
            LOGGER,
            OMNI_REL_DIR,
            _apply_contrast_output_triggers,
            _clear_nodb_cache_and_locks,
            _contrast_topaz_ids_from_mapping,
            _copy_archive_root_with_projection_retry,
            _copy_mutable_root_sidecar,
            _link_shared_root_sidecars,
            _merge_contrast_parquet,
            _post_watershed_run_cleanup,
            _resolve_base_scenario_key,
            _resolve_contrast_scenario_wd,
            _update_nodb_wd,
            copy_version_for_clone,
            nodir_resolve,
            pick_existing_parquet_path,
        )

        return (
            LOGGER,
            OMNI_REL_DIR,
            copy_version_for_clone,
            nodir_resolve,
            pick_existing_parquet_path,
            _clear_nodb_cache_and_locks,
            _link_shared_root_sidecars,
            _copy_archive_root_with_projection_retry,
            _copy_mutable_root_sidecar,
            _update_nodb_wd,
            _resolve_base_scenario_key,
            _resolve_contrast_scenario_wd,
            _contrast_topaz_ids_from_mapping,
            _merge_contrast_parquet,
            _apply_contrast_output_triggers,
            _post_watershed_run_cleanup,
        )

    def run_contrast(
        self,
        contrast_id: str,
        contrast_name: str,
        contrasts: Dict[int | str, str],
        wd: str,
        runid: str,
        control_scenario_key: str,
        contrast_scenario_key: str,
        wepp_bin: str = "wepp_dcc52a6",
        output_options: Optional[Dict[str, bool]] = None,
    ) -> str:
        from wepppy.nodb.core import Wepp

        (
            logger,
            omni_rel_dir,
            copy_version_for_clone,
            nodir_resolve,
            pick_existing_parquet_path,
            clear_nodb_cache_and_locks,
            link_shared_root_sidecars,
            copy_archive_root_with_projection_retry,
            copy_mutable_root_sidecar,
            update_nodb_wd,
            resolve_base_scenario_key,
            resolve_contrast_scenario_wd,
            contrast_topaz_ids_from_mapping,
            merge_contrast_parquet,
            apply_contrast_output_triggers,
            post_watershed_run_cleanup,
        ) = self._run_contrast_contract_refs()

        new_wd = _join(wd, omni_rel_dir, "contrasts", contrast_id)
        pup_relpath = os.path.relpath(new_wd, wd)

        if _exists(new_wd):
            _reset_workspace(new_wd, logger=logger)
            clear_nodb_cache_and_locks(runid, pup_relpath)

        os.makedirs(new_wd)
        copy_version_for_clone(wd, new_wd)

        os.makedirs(_join(new_wd, "soils"), exist_ok=True)
        os.makedirs(_join(new_wd, "landuse"), exist_ok=True)

        for dirname in ("climate", "watershed"):
            src_dir = _join(wd, dirname)
            src_archive = _join(wd, f"{dirname}.nodir")
            if os.path.isdir(src_dir):
                src = src_dir
                dst = _join(new_wd, dirname)
            elif os.path.isfile(src_archive):
                src = src_archive
                dst = _join(new_wd, f"{dirname}.nodir")
            else:
                continue
            if not _exists(dst):
                os.symlink(src, dst)
            link_shared_root_sidecars(wd, new_wd, dirname)

        for root in ("landuse", "soils"):
            resolved_root = nodir_resolve(wd, root, view="effective")
            if resolved_root is None:
                continue

            if resolved_root.form == "archive":
                copy_archive_root_with_projection_retry(
                    wd,
                    new_wd,
                    root,
                    purpose=f"omni-run-contrast-{root}",
                )
                copy_mutable_root_sidecar(wd, new_wd, root)
                continue

            if resolved_root.form == "dir":
                src_root = Path(resolved_root.dir_path)
                if resolved_root.inner_path:
                    src_root = src_root / resolved_root.inner_path

                if not src_root.is_dir():
                    logger.warning(
                        "Skipping %s copy for contrast clone; source directory missing: %s",
                        root,
                        src_root,
                    )
                    continue

                dst_root = Path(new_wd) / root
                if dst_root.exists():
                    shutil.rmtree(dst_root)
                shutil.copytree(str(src_root), str(dst_root))
                copy_mutable_root_sidecar(wd, new_wd, root)

        symlink_entries = {
            "climate.nodb",
            "watershed.nodb",
            "landuse.nodb",
            "soils.nodb",
            "unitizer.nodb",
            "treatments.nodb",
        }
        symlink_nodb_files = {entry for entry in symlink_entries if entry.endswith(".nodb")}

        for fn in os.listdir(wd):
            if fn in symlink_entries:
                src = _join(wd, fn)
                dst = _join(new_wd, fn)
                if not _exists(dst):
                    os.symlink(src, dst)

        for nodb_fn in os.listdir(wd):
            if not nodb_fn.endswith(".nodb"):
                continue
            if nodb_fn in symlink_nodb_files:
                continue
            src = _join(wd, nodb_fn)
            if not _isfile(src):
                continue
            dst = _join(new_wd, nodb_fn)
            if not _exists(dst):
                shutil.copy(src, dst)

            with open(dst, "r") as f:
                data = json.load(f)

            update_nodb_wd(data, new_wd, parent_wd=wd)

            with open(dst, "w") as fp:
                json.dump(data, fp)
                fp.flush()
                os.fsync(fp.fileno())

        wepp = Wepp.getInstance(new_wd)
        wepp.wepp_bin = wepp_bin
        wepp.clean()

        og_runs_dir = _join(wd, "wepp", "runs/")
        omni_runs_dir = _join(new_wd, "wepp", "runs/")
        for fn in os.listdir(og_runs_dir):
            entry_name = _split(fn)[-1]
            if entry_name in ("pw0.run", "pw0.err"):
                continue
            src = _join(og_runs_dir, fn)
            if not _isfile(src):
                continue
            dst = _join(omni_runs_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

        old_prefix = _join(wd, "omni")
        new_prefix = _join(wd, omni_rel_dir)
        normalized_contrasts: Dict[int | str, str] = {}
        for topaz_id, wepp_id_path in contrasts.items():
            normalized_path = wepp_id_path
            if isinstance(wepp_id_path, str) and wepp_id_path.startswith(old_prefix):
                candidate = new_prefix + wepp_id_path[len(old_prefix) :]
                if _exists(f"{candidate}.pass.dat"):
                    logger.info("Updating contrast path %s -> %s", wepp_id_path, candidate)
                    normalized_path = candidate
            normalized_contrasts[topaz_id] = normalized_path

        base_key = resolve_base_scenario_key(wd)
        control_wd = resolve_contrast_scenario_wd(wd, control_scenario_key, base_key)
        contrast_wd = resolve_contrast_scenario_wd(wd, contrast_scenario_key, base_key)
        contrast_topaz_ids = contrast_topaz_ids_from_mapping(normalized_contrasts, contrast_wd)
        if not contrast_topaz_ids and control_scenario_key != contrast_scenario_key:
            raise ValueError(f"No contrast hillslopes detected for {contrast_name}.")

        control_landuse = pick_existing_parquet_path(control_wd, "landuse/landuse.parquet")
        if control_landuse is None:
            raise FileNotFoundError(
                f"Missing landuse parquet (landuse/landuse.parquet) in {control_wd}"
            )
        contrast_landuse = pick_existing_parquet_path(contrast_wd, "landuse/landuse.parquet")
        if contrast_landuse is None:
            raise FileNotFoundError(
                f"Missing landuse parquet (landuse/landuse.parquet) in {contrast_wd}"
            )
        control_soils = pick_existing_parquet_path(control_wd, "soils/soils.parquet")
        if control_soils is None:
            raise FileNotFoundError(f"Missing soils parquet (soils/soils.parquet) in {control_wd}")
        contrast_soils = pick_existing_parquet_path(contrast_wd, "soils/soils.parquet")
        if contrast_soils is None:
            raise FileNotFoundError(
                f"Missing soils parquet (soils/soils.parquet) in {contrast_wd}"
            )

        merge_contrast_parquet(
            control_parquet_fn=str(control_landuse),
            contrast_parquet_fn=str(contrast_landuse),
            output_parquet_fn=str(Path(new_wd) / "landuse.parquet"),
            contrast_topaz_ids=contrast_topaz_ids,
            label="landuse",
        )
        merge_contrast_parquet(
            control_parquet_fn=str(control_soils),
            contrast_parquet_fn=str(contrast_soils),
            output_parquet_fn=str(Path(new_wd) / "soils.parquet"),
            contrast_topaz_ids=contrast_topaz_ids,
            label="soils",
        )

        if output_options is None:
            output_options = {}
        wepp._contrast_output_options = dict(output_options)
        wepp.make_watershed_run(
            wepp_id_paths=list(normalized_contrasts.values()),
            output_options=output_options,
        )
        apply_contrast_output_triggers(wepp, output_options)
        wepp.run_watershed()
        post_watershed_run_cleanup(wepp)
        wepp.report_loss()

        return new_wd

    @staticmethod
    def _omni_clone_contract_refs():
        from wepppy.nodb.mods.omni.omni import (
            LOGGER,
            OMNI_REL_DIR,
            _clear_nodb_cache_and_locks,
            _copy_archive_root_with_projection_retry,
            _copy_mutable_root_sidecar,
            _link_shared_root_sidecars,
            _scenario_name_from_scenario_definition,
            _update_nodb_wd,
            nodir_resolve,
        )

        return (
            LOGGER,
            OMNI_REL_DIR,
            nodir_resolve,
            _scenario_name_from_scenario_definition,
            _clear_nodb_cache_and_locks,
            _link_shared_root_sidecars,
            _update_nodb_wd,
            _copy_archive_root_with_projection_retry,
            _copy_mutable_root_sidecar,
        )

    def omni_clone(self, scenario_def: Dict[str, Any], wd: str, runid: str) -> str:
        (
            logger,
            omni_rel_dir,
            nodir_resolve,
            scenario_name_from_scenario_definition,
            clear_nodb_cache_and_locks,
            link_shared_root_sidecars,
            update_nodb_wd,
            copy_archive_root_with_projection_retry,
            copy_mutable_root_sidecar,
        ) = self._omni_clone_contract_refs()

        scenario_name = scenario_name_from_scenario_definition(scenario_def)
        new_wd = _join(wd, omni_rel_dir, "scenarios", scenario_name)
        pup_relpath = os.path.relpath(new_wd, wd)

        if _exists(new_wd):
            _reset_workspace(new_wd, logger=logger)
            clear_nodb_cache_and_locks(runid, pup_relpath)

        os.makedirs(new_wd)

        for dirname in ("climate", "watershed"):
            src_dir = _join(wd, dirname)
            src_archive = _join(wd, f"{dirname}.nodir")
            if os.path.isdir(src_dir):
                src = src_dir
                dst = _join(new_wd, dirname)
            elif os.path.isfile(src_archive):
                src = src_archive
                dst = _join(new_wd, f"{dirname}.nodir")
            else:
                continue
            if not _exists(dst):
                os.symlink(src, dst)
            link_shared_root_sidecars(wd, new_wd, dirname)

        for fn in os.listdir(wd):
            if fn in ["dem", "climate.nodb", "dem.nodb", "watershed.nodb"]:
                src = _join(wd, fn)
                dst = _join(new_wd, fn)
                if not _exists(dst):
                    os.symlink(src, dst)
            elif fn in ["disturbed", "rap"]:
                src = _join(wd, fn)
                dst = _join(new_wd, fn)
                if not _exists(dst):
                    shutil.copytree(src, dst)
            elif fn.endswith(".nodb"):
                if fn == "omni.nodb":
                    continue

                src = _join(wd, fn)
                dst = _join(new_wd, fn)
                if not _exists(dst):
                    shutil.copy(src, dst)

                with open(dst, "r") as f:
                    data = json.load(f)

                update_nodb_wd(data, new_wd, parent_wd=wd)

                with open(dst, "w") as fp:
                    json.dump(data, fp)
                    fp.flush()
                    os.fsync(fp.fileno())

        soils_root = nodir_resolve(wd, "soils", view="effective")
        if soils_root is not None:
            if soils_root.form == "archive":
                copy_archive_root_with_projection_retry(
                    wd,
                    new_wd,
                    "soils",
                    purpose="omni-clone-soils",
                )
                copy_mutable_root_sidecar(wd, new_wd, "soils")
            elif soils_root.form == "dir":
                src_root = Path(soils_root.dir_path)
                if soils_root.inner_path:
                    src_root = src_root / soils_root.inner_path

                if not src_root.is_dir():
                    logger.warning(
                        "Skipping soils copy for omni clone; source directory missing: %s",
                        src_root,
                    )
                else:
                    dst_root = Path(new_wd) / "soils"
                    if dst_root.exists():
                        shutil.rmtree(dst_root)
                    shutil.copytree(str(src_root), str(dst_root))
                    copy_mutable_root_sidecar(wd, new_wd, "soils")

        landuse_root = nodir_resolve(wd, "landuse", view="effective")
        if landuse_root is not None:
            if landuse_root.form == "archive":
                os.makedirs(_join(new_wd, "landuse"), exist_ok=True)
                copy_mutable_root_sidecar(wd, new_wd, "landuse")
            elif landuse_root.form == "dir":
                src_root = Path(landuse_root.dir_path)
                if landuse_root.inner_path:
                    src_root = src_root / landuse_root.inner_path

                if not src_root.is_dir():
                    logger.warning(
                        "Skipping landuse copy for omni clone; source directory missing: %s",
                        src_root,
                    )
                else:
                    dst_root = Path(new_wd) / "landuse"
                    if dst_root.exists():
                        shutil.rmtree(dst_root)
                    shutil.copytree(str(src_root), str(dst_root))
                    copy_mutable_root_sidecar(wd, new_wd, "landuse")

        for fn in os.listdir(wd):
            if fn == "_pups":
                continue

            src = _join(wd, fn)
            if os.path.isdir(src):
                dst = _join(new_wd, fn)

                if not _exists(dst):
                    try:
                        for root, dirs, _ in os.walk(src):
                            for dir_name in dirs:
                                src_dir = _join(root, dir_name)
                                rel_path = os.path.relpath(src_dir, src)
                                dst_dir = _join(dst, rel_path)
                                if not _exists(dst_dir):
                                    os.makedirs(dst_dir, exist_ok=True)
                    except PermissionError as exc:
                        logger.warning(
                            "Permission denied while creating Omni clone directory tree from %s to %s: %s",
                            src,
                            dst,
                            exc,
                        )
                    except OSError as exc:
                        logger.warning(
                            "Error creating Omni clone directory tree from %s to %s: %s",
                            src,
                            dst,
                            exc,
                        )

                if not _exists(dst):
                    os.makedirs(dst, exist_ok=True)

        if _exists(_join(new_wd, "READONLY")):
            os.remove(_join(new_wd, "READONLY"))

        return new_wd

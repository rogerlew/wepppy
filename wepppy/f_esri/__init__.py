import os
import stat
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


class FEsriError(RuntimeError):
    """Raised when interacting with the f-esri container fails."""


DEFAULT_CONTAINER_NAME = os.getenv("F_ESRI_CONTAINER", "wepppy-f-esri")
DEFAULT_TIMEOUT = int(os.getenv("F_ESRI_COMMAND_TIMEOUT", "1800"))
OGR2OGR_BINARY = os.getenv("F_ESRI_OGR2OGR_BINARY", "ogr2ogr")
_FILE_PERMISSION_BITS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
_DIR_PERMISSION_BITS = _FILE_PERMISSION_BITS | stat.S_IXUSR | stat.S_IXGRP


def _run_docker_command(args: Iterable[str], *, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """
    Run a docker command and return the completed process.
    """
    if shutil.which("docker") is None:
        raise FEsriError("Docker CLI not found in PATH. Install the Docker client or mount it into this container.")

    try:
        return subprocess.run(
            ["docker", *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except PermissionError as exc:
        raise FEsriError("Docker CLI is present but access to the Docker socket was denied.") from exc
    except FileNotFoundError as exc:
        raise FEsriError("Docker CLI not available in the current environment.") from exc


def has_f_esri(container_name: str = DEFAULT_CONTAINER_NAME) -> bool:
    """
    Determine whether the f-esri container is running.
    """
    result = _run_docker_command(["ps", "-q", "--filter", f"name={container_name}"], timeout=15)
    return bool(result.stdout.strip())


def _docker_exec(
    container_name: str,
    exec_args: Iterable[str],
    *,
    timeout: Optional[int] = None,
    user: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    Execute a command inside the specified container.
    """
    if not has_f_esri(container_name):
        raise FEsriError(f"f-esri container '{container_name}' is not running.")

    docker_exec_args = ["exec"]
    if user:
        docker_exec_args.extend(["--user", user])
    docker_exec_args.extend([container_name, *exec_args])
    return _run_docker_command(docker_exec_args, timeout=timeout)


def _resolve_current_user_spec() -> Optional[str]:
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        return f"{os.getuid()}:{os.getgid()}"
    return None


def _ensure_mode_bits(path: Path, *, required_bits: int) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return

    if stat.S_ISLNK(mode):
        return

    desired_mode = mode | required_bits
    if desired_mode != mode:
        os.chmod(path, desired_mode)


def _set_gdb_tree_permissions(gdb_path: Path) -> None:
    if not gdb_path.exists():
        return

    _ensure_mode_bits(gdb_path.parent, required_bits=_DIR_PERMISSION_BITS)

    if gdb_path.is_dir():
        for root, dirs, files in os.walk(gdb_path):
            root_path = Path(root)
            _ensure_mode_bits(root_path, required_bits=_DIR_PERMISSION_BITS)
            for dirname in dirs:
                _ensure_mode_bits(root_path / dirname, required_bits=_DIR_PERMISSION_BITS)
            for filename in files:
                _ensure_mode_bits(root_path / filename, required_bits=_FILE_PERMISSION_BITS)
        _ensure_mode_bits(gdb_path, required_bits=_DIR_PERMISSION_BITS)
        return

    _ensure_mode_bits(gdb_path, required_bits=_FILE_PERMISSION_BITS)


def c2c_gpkg_to_gdb(
    gpkg_fn: str,
    gdb_fn: str,
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    timeout: int = DEFAULT_TIMEOUT,
    zip_output: bool = True,
    verbose: bool = False,
    ogr2ogr_binary: str = OGR2OGR_BINARY,
) -> str:
    """
    Convert a GeoPackage to FileGDB by executing ogr2ogr inside the running f-esri container.
    """
    gpkg_path = Path(gpkg_fn).resolve()
    gdb_path = Path(gdb_fn).resolve()

    if not gpkg_path.exists():
        raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")

    if gdb_path.exists():
        if gdb_path.is_dir():
            shutil.rmtree(gdb_path)
        else:
            gdb_path.unlink()

    gdb_path.parent.mkdir(parents=True, exist_ok=True)

    exec_cmd = [
        ogr2ogr_binary,
        "-f",
        "FileGDB",
        str(gdb_path),
        str(gpkg_path),
    ]

    if verbose:
        print("docker exec", container_name, " ".join(exec_cmd))

    result = _docker_exec(
        container_name,
        exec_cmd,
        timeout=timeout,
        user=_resolve_current_user_spec(),
    )
    if result.returncode != 0:
        raise FEsriError(
            "Failed to convert GeoPackage to FileGDB via f-esri container:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    _set_gdb_tree_permissions(gdb_path)

    if verbose and result.stdout:
        print(result.stdout)

    if zip_output:
        zip_target = gdb_path.with_suffix(gdb_path.suffix + ".zip") if gdb_path.suffix else gdb_path.with_suffix(".zip")
        if zip_target.exists():
            zip_target.unlink()
        shutil.make_archive(str(gdb_path), "zip", str(gdb_path))
        _set_gdb_tree_permissions(zip_target)

    return str(gdb_path)


def gpkg_to_gdb(
    gpkg_fn: str,
    gdb_fn: str,
    *,
    container_name: str = DEFAULT_CONTAINER_NAME,
    timeout: int = DEFAULT_TIMEOUT,
    zip_output: bool = True,
    verbose: bool = False,
) -> str:
    """
    Backwards compatible wrapper that calls the container-to-container implementation.
    """
    return c2c_gpkg_to_gdb(
        gpkg_fn,
        gdb_fn,
        container_name=container_name,
        timeout=timeout,
        zip_output=zip_output,
        verbose=verbose,
    )


__all__ = [
    "FEsriError",
    "c2c_gpkg_to_gdb",
    "gpkg_to_gdb",
    "has_f_esri",
]

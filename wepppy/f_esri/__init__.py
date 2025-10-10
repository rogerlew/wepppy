import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


class FEsriError(RuntimeError):
    """Raised when interacting with the f-esri container fails."""


DEFAULT_CONTAINER_NAME = os.getenv("F_ESRI_CONTAINER", "wepppy-f-esri")
DEFAULT_TIMEOUT = int(os.getenv("F_ESRI_COMMAND_TIMEOUT", "600"))
OGR2OGR_BINARY = os.getenv("F_ESRI_OGR2OGR_BINARY", "ogr2ogr")


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


def _docker_exec(container_name: str, exec_args: Iterable[str], *, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """
    Execute a command inside the specified container.
    """
    if not has_f_esri(container_name):
        raise FEsriError(f"f-esri container '{container_name}' is not running.")

    return _run_docker_command(["exec", container_name, *exec_args], timeout=timeout)


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

    result = _docker_exec(container_name, exec_cmd, timeout=timeout)
    if result.returncode != 0:
        raise FEsriError(
            "Failed to convert GeoPackage to FileGDB via f-esri container:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    if verbose and result.stdout:
        print(result.stdout)

    if zip_output:
        zip_target = gdb_path.with_suffix(gdb_path.suffix + ".zip") if gdb_path.suffix else gdb_path.with_suffix(".zip")
        if zip_target.exists():
            zip_target.unlink()
        shutil.make_archive(str(gdb_path), "zip", str(gdb_path))

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

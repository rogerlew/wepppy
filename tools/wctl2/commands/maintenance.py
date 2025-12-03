from __future__ import annotations

import grp
import os
import pwd
import stat
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Tuple

import typer

from ..context import CLIContext


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _lookup_user_uid(username: str) -> Optional[str]:
    try:
        return str(pwd.getpwnam(username).pw_uid)
    except KeyError:
        return None


def _lookup_group_gid(group: str) -> Optional[str]:
    try:
        return str(grp.getgrnam(group).gr_gid)
    except KeyError:
        return None


def _resolve_runtime_uid_gid(context: CLIContext) -> Tuple[str, str]:
    raw_uid = context.env_value("UID")
    raw_gid = context.env_value("GID")

    uid = (raw_uid or "").strip() or _lookup_user_uid("roger") or "1000"
    gid = (raw_gid or "").strip() or _lookup_group_gid("docker") or "993"

    return uid, gid


def _run_host_command(context: CLIContext, command: Sequence[str]) -> int:
    return subprocess.run(
        list(command),
        cwd=str(context.project_dir),
        env=context.environment,
    ).returncode


def _chmod(path: Path, mode: int) -> None:
    path.chmod(mode)


def _chown_recursive(path: Path, spec: str) -> None:
    subprocess.run(["chown", "-R", spec, str(path)], check=True)


def _chmod_safe(path: Path, mode: int) -> None:
    try:
        _chmod(path, mode)
    except PermissionError as exc:
        typer.echo(f"Failed to chmod {path}: {exc}", err=True)
        raise typer.Exit(1)


def _chown_safe(path: Path, spec: str) -> None:
    try:
        _chown_recursive(path, spec)
    except subprocess.CalledProcessError as exc:
        typer.echo(f"Failed to chown {path}: {exc}", err=True)
        raise typer.Exit(exc.returncode)
    except PermissionError as exc:
        typer.echo(f"Permission denied while chowning {path}: {exc}", err=True)
        raise typer.Exit(1)


def register(app: typer.Typer) -> None:
    @app.command(
        "build-static-assets",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def build_static_assets(ctx: typer.Context) -> None:
        context = _context(ctx)
        script = context.project_dir / "wepppy" / "weppcloud" / "static-src" / "build-static-assets.sh"
        if not script.exists() or not os.access(script, os.X_OK):
            typer.echo(f"Static asset build script not found at {script}", err=True)
            raise typer.Exit(1)

        command = [str(script)]
        if context.is_prod():
            command.append("--prod")
        command.extend(ctx.args)
        exit_code = _run_host_command(context, command)
        raise typer.Exit(exit_code)

    @app.command("restore-docker-data-permissions")
    def restore_docker_data_permissions(ctx: typer.Context) -> None:
        context = _context(ctx)
        data_root = context.project_dir / ".docker-data"
        if not data_root.exists():
            typer.echo(f"No .docker-data directory at {data_root}; nothing to do.")
            raise typer.Exit(0)

        app_uid, app_gid = _resolve_runtime_uid_gid(context)

        postgres = data_root / "postgres"
        if postgres.exists():
            typer.echo(f"Fixing ownership for {postgres} (postgres:postgres).")
            _chown_safe(postgres, "999:999")
            _chmod_safe(postgres, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        else:
            typer.echo(f"Skipping missing {postgres}.")

        postgres_backups = data_root / "postgres-backups"
        if postgres_backups.exists():
            typer.echo(f"Fixing ownership for {postgres_backups} (postgres backups).")
            _chown_safe(postgres_backups, "999:999")
            _chmod_safe(
                postgres_backups,
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP,
            )
        else:
            typer.echo(f"Skipping missing {postgres_backups}.")

        redis = data_root / "redis"
        if redis.exists():
            typer.echo(f"Fixing ownership for {redis} (redis).")
            _chown_safe(redis, "999:999")
            _chmod_safe(redis, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            redis_aof = redis / "appendonlydir"
            if redis_aof.exists():
                _chmod_safe(redis_aof, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        else:
            typer.echo(f"Skipping missing {redis}.")

        weppcloud = data_root / "weppcloud"
        if weppcloud.exists():
            typer.echo(
                f"Fixing ownership for {weppcloud} (uid:gid {app_uid}:{app_gid})."
            )
            _chown_safe(weppcloud, f"{app_uid}:{app_gid}")
            _chmod_safe(
                weppcloud,
                stat.S_IRUSR
                | stat.S_IWUSR
                | stat.S_IXUSR
                | stat.S_IRGRP
                | stat.S_IWGRP
                | stat.S_IXGRP,
            )
            weppcloud_logs = weppcloud / "logs"
            if weppcloud_logs.exists():
                _chmod_safe(
                    weppcloud_logs,
                    stat.S_IRUSR
                    | stat.S_IWUSR
                    | stat.S_IXUSR
                    | stat.S_IRGRP
                    | stat.S_IWGRP
                    | stat.S_IXGRP,
                )
        else:
            typer.echo(f"Skipping missing {weppcloud}.")

        typer.echo("Permission restoration completed.")
        raise typer.Exit(0)

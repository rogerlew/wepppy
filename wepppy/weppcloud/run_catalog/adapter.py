"""Explicit deployment configuration and bounded, fork-safe SQL mirroring."""

from dataclasses import dataclass
from datetime import timezone
import os
import logging
import time

import sqlalchemy as sa

from wepppy.config.secrets import get_secret
from .paths import Roots
from .repository import invalidate
from .schema import runs

__all__ = ["Settings", "initialize", "get_engine", "database_url", "Adapter"]


@dataclass(frozen=True)
class Settings:
    commit_mode: str = "disabled"
    write_mode: str = "timestamp_only"
    read_mode: str = "legacy"

    @classmethod
    def from_environ(cls):
        settings = cls(os.getenv("WEPPPY_PROJECT_COMMIT_MODE", "disabled"),
                       os.getenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only"),
                       os.getenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy"))
        if settings.commit_mode not in {"disabled", "postgres"} or settings.write_mode not in {"timestamp_only", "catalog"} or settings.read_mode not in {"legacy", "postgres"}:
            raise ValueError("Unknown project catalog mode")
        if settings.read_mode == "postgres" and (settings.commit_mode != "postgres" or settings.write_mode != "catalog"):
            raise ValueError("PostgreSQL catalog reads require catalog writes and persistence integration")
        if settings.write_mode == "catalog" and settings.commit_mode != "postgres":
            raise ValueError("Catalog writes require persistence integration")
        return settings


def database_url():
    configured = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    if configured:
        url = sa.engine.make_url(configured)
        if url.get_backend_name() != "postgresql":
            raise ValueError("Run catalog requires PostgreSQL")
        return url
    return sa.URL.create("postgresql", username=os.getenv("POSTGRES_USER", "wepppy"),
                         password=get_secret("POSTGRES_PASSWORD", required=True),
                         host=os.getenv("POSTGRES_HOST", "postgres"),
                         port=int(os.getenv("POSTGRES_PORT", "5432")),
                         database=os.getenv("POSTGRES_DB", "wepppy"))


_engines = {}


def get_engine(refresh=False):
    key = (os.getpid(), refresh)
    for inherited in list(_engines):
        if inherited[0] != key[0]:
            _engines.pop(inherited).dispose(close=False)
    if key not in _engines:
        _engines[key] = sa.create_engine(
            database_url(), pool_size=3 if refresh else 2, max_overflow=0,
            pool_timeout=0.25, hide_parameters=True,
            connect_args={"connect_timeout": 1, "options": "-c lock_timeout=250ms -c statement_timeout=1000ms"},
            isolation_level="READ COMMITTED",
        )
    return _engines[key]


class Adapter:
    def __init__(self, settings, roots=None, engine_factory=get_engine):
        self.settings = settings
        self.roots = roots or Roots.from_environ()
        self.engine_factory = engine_factory

    def __call__(self, event):
        started = time.monotonic()
        direct = self.roots.matches(event.runid, event.wd)
        parent_path, separator, child_path = os.path.abspath(event.wd).partition(os.sep + "_pups" + os.sep)
        timestamp_only_child = event.source == "nodb" and separator and child_path and self.roots.matches(event.runid, parent_path)
        if not direct and not timestamp_only_child:
            raise ValueError("source_identity_mismatch")
        with self.engine_factory().begin() as connection:
            if event.source == "nodb":
                identifiers = event.runid.split(";;")
                child = len(identifiers) in {3, 5} and identifiers[-2] in {"omni", "omni-contrast"} and not (len(identifiers) == 3 and identifiers[0] in {"batch", "culvert"})
                parent = ";;".join(identifiers[:-2]) if child else event.runid
                timestamp = event.committed_at.astimezone(timezone.utc).replace(tzinfo=None)
                connection.execute(runs.update().where(runs.c.runid == parent).values(
                    last_modified=sa.func.greatest(runs.c.last_modified, timestamp)))
            if direct and self.settings.write_mode == "catalog" and (event.source != "nodb" or event.controller_filename == "ron.nodb"):
                invalidate(connection, event.runid, event.committed_at)
        logging.getLogger(__name__).info("project_commit_mirror_completed pid=%s runid=%s source=%s elapsed_seconds=%.6f",
                                        os.getpid(), event.runid, event.source, time.monotonic() - started)


def initialize():
    settings = Settings.from_environ()
    if settings.commit_mode == "disabled":
        return settings
    get_engine()
    from wepppy.nodb.persistence_events import register_project_commit_observer
    register_project_commit_observer(Adapter(settings))
    return settings

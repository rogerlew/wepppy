import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from wepppy.weppcloud.configuration import _build_postgres_uri
from wepppy.weppcloud.run_catalog import repository
from wepppy.weppcloud.run_catalog.schema import metadata, runs, catalog
from wepppy.weppcloud.run_catalog.paths import Roots
from tests.rq.test_project_rq_archive import archive_rq_environment

pytestmark = pytest.mark.integration
POSTGRES_URI = _build_postgres_uri()


@pytest.fixture
def database():
    schema = "catalog_test_" + uuid4().hex
    admin = sa.create_engine(POSTGRES_URI, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    engine = sa.create_engine(POSTGRES_URI, hide_parameters=True, connect_args={"options": "-csearch_path=" + schema})
    try:
        runs.create(engine)
        path = Path(__file__).parents[2] / "wepppy/weppcloud/migrations/versions/d30c91a7b802_add_run_catalog.py"
        spec = importlib.util.spec_from_file_location("catalog_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin.dispose()


def register(engine):
    with engine.begin() as connection:
        connection.execute(runs.insert().values(id=1, runid="test"))
        assert repository.seed(connection) == [1]
        assert repository.seed(connection) == []


def test_sweep_isolates_row_publication_failure(database, tmp_path, monkeypatch):
    from wepppy.weppcloud.run_catalog import service
    from wepppy.weppcloud.run_catalog.extractor import extract
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    with database.begin() as connection:
        connection.execute(runs.insert(), [{"id": identifier, "runid": f"run-{identifier}"} for identifier in range(1, 4)])
        repository.seed(connection)
    for identifier in range(1, 4):
        project = tmp_path / "ru" / f"run-{identifier}"
        project.mkdir(parents=True)
        (project / "ron.nodb").write_text('{"_name":"valid"}')

    def bad_snapshot(runid, **kwargs):
        snapshot = extract(runid, **kwargs)
        if runid != "run-3":
            snapshot.sources["ron"].values["name"] = "invalid\x00text"
        return snapshot

    refresh = repository.refresh
    monkeypatch.setattr(repository, "refresh", lambda *args, **kwargs: refresh(*args, extractor=bad_snapshot, **kwargs))
    before = repository.utcnow()
    result = service.sweep(database, roots, apply=True)
    assert result["attempted"] == 3
    assert result["outcomes"] == {1: "retry", 2: "retry", 3: "ready"}
    with database.connect() as connection:
        rows = list(connection.execute(sa.select(catalog).order_by(catalog.c.run_id)).mappings())
        for row in rows[:2]:
            assert row["indexed_revision"] == 0
            assert row["last_error_code"] == "catalog_publish_failed"
            assert (row["next_attempt_at"] - before).total_seconds() >= 60
        assert rows[2]["name"] == "valid"


def test_extreme_ttl_cannot_starve_later_rows(database, tmp_path):
    from wepppy.weppcloud.run_catalog import service
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    with database.begin() as connection:
        connection.execute(runs.insert(), [{"id": identifier, "runid": f"run-{identifier}"} for identifier in range(1, 4)])
    for identifier in range(1, 4):
        project = tmp_path / "ru" / f"run-{identifier}"
        project.mkdir(parents=True)
        (project / "ron.nodb").write_text('{"_name":"usable"}')
        if identifier < 3:
            (project / "TTL").write_text('{"expires_at":"0001-01-01T00:00:00+01:00"}')
    assert service.sweep(database, roots, apply=True)["outcomes"] == {1: "ready", 2: "ready", 3: "ready"}
    with database.connect() as connection:
        assert list(connection.scalars(sa.select(catalog.c.name))) == ["usable"] * 3
        assert list(connection.scalars(sa.select(catalog.c.ttl_deletion_at))) == [None] * 3


def test_origin_probe_is_connection_bound_and_cleans_locks(database):
    from wepppy.weppcloud.run_catalog.service import probe_origin
    from secrets import randbits
    held, control = randbits(62), randbits(62)
    other = sa.create_engine(sa.engine.make_url(POSTGRES_URI).set(database="postgres"), hide_parameters=True)
    try:
        with database.begin() as coordinator:
            assert coordinator.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(sa.cast(held, sa.BigInteger))))
            with database.begin() as consumer:
                assert probe_origin(consumer, held, control)["matches_origin"] is True
            with other.begin() as consumer:
                assert probe_origin(consumer, held, control)["matches_origin"] is False
            assert coordinator.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(sa.cast(control, sa.BigInteger))))
            with database.begin() as consumer:
                assert probe_origin(consumer, held, control)["matches_origin"] is False
        with database.begin() as consumer:
            result = probe_origin(consumer, held, control)
            assert result == {"held_acquired": True, "control_acquired": True, "matches_origin": False}
    finally:
        other.dispose()


def test_compare_unreadable_is_inconclusive(database, tmp_path, monkeypatch):
    from wepppy.weppcloud.run_catalog import service
    from wepppy.weppcloud.run_catalog.extractor import Snapshot, Observation
    register(database)
    with database.begin() as connection:
        connection.execute(catalog.update().values(ron_state="unreadable", ttl_state="unreadable", readonly_state="unreadable"))
    monkeypatch.setattr(service, "extract", lambda *args: Snapshot(None, {source: Observation("unreadable") for source in ("ron", "readonly", "ttl")}))
    report = service.compare(database)["rows"][0]
    assert report["state"] == "inconclusive"
    assert report["unreadable_sources"] == ["ron", "readonly", "ttl"]


def test_preflight_never_grants_promotion_authority(database):
    from wepppy.weppcloud.run_catalog import service
    from wepppy.weppcloud.run_catalog.adapter import Settings
    operational = {"eligible_consumers": 1, "incompatible_consumers": [], "sweep": {"completed_at": repository.utcnow().isoformat(), "state": "completed"}}
    with database.begin() as connection:
        result = service.preflight(connection, Settings("postgres", "catalog"), operational)
        assert result["technical_ready"] is True
        assert result["gate_status"] == "operator_evidence_required"
        assert "ready" not in result
        assert "consumer_connection_bound_origin_proof" in result["promotion_requires"]
        result = service.preflight(connection, Settings("postgres", "catalog"), {})
        assert result["technical_ready"] is False


def test_preflight_rejects_unreadable_source_hidden_by_other_diagnostic(database):
    from wepppy.weppcloud.run_catalog import service
    from wepppy.weppcloud.run_catalog.adapter import Settings
    register(database)
    now = repository.utcnow()
    with database.begin() as connection:
        connection.execute(catalog.update().values(ron_state="ready", readonly_state="ready", ttl_state="unreadable",
            last_error_code="unsupported_map", reconciled_at=now, dirty_since=now))
        operational = {"eligible_consumers": 1, "incompatible_consumers": [], "sweep": {"completed_at": now.isoformat(), "state": "completed"}}
        result = service.preflight(connection, Settings("postgres", "catalog"), operational)
        assert result["technical_ready"] is False
        assert result["observed"]["transient_failures"] == 1
        assert "source_observations_unresolved" in result["failures"]


@pytest.mark.parametrize("trusted_alias", [False, True])
def test_archive_restore_invalidates_without_nodb_save(database, archive_rq_environment, monkeypatch, trusted_alias):
    import zipfile
    from wepppy.nodb import persistence_events
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    project, tmp_path, _, _ = archive_rq_environment
    root = tmp_path / "demo"
    (root / "archives").mkdir(parents=True)
    (root / "ron.nodb").write_text('{"_name":"Before restore"}')
    roots = Roots(primary=str(tmp_path / "primary"), legacy=str(tmp_path))
    if trusted_alias:
        alias = tmp_path / "trusted-root-alias"
        alias.symlink_to(tmp_path)
        roots = Roots(primary=str(tmp_path / "primary"), legacy=str(alias))
        monkeypatch.setattr(project, "get_wd", lambda runid: str(alias / runid))
    with database.begin() as connection:
        connection.execute(runs.insert().values(id=1, runid="demo"))
        repository.seed(connection)
    repository.refresh(database, 1, roots)
    monkeypatch.setattr(persistence_events, "_observer", Adapter(Settings("postgres", "catalog"), roots, lambda: database))
    with zipfile.ZipFile(root / "archives/restored.zip", "w") as archive:
        archive.writestr("ron.nodb", '{"_name":"After restore"}')
        archive.writestr("READONLY", "")
    project.restore_archive_rq("demo", "restored.zip")
    with database.connect() as connection:
        assert connection.scalar(sa.select(catalog.c.dirty_revision)) == 2
        assert connection.scalar(sa.select(catalog.c.name)) == "Before restore"
    repository.refresh(database, 1, roots)
    with database.connect() as connection:
        assert connection.scalar(sa.select(catalog.c.name)) == "After restore"
        assert connection.scalar(sa.select(catalog.c.readonly)) is True


@pytest.mark.slow
def test_actual_save_notification_latency_and_database_refusal(database, tmp_path, monkeypatch, caplog):
    import json
    import time
    from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
    from wepppy.nodb import base, persistence_events
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    register(database)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    directory = tmp_path / "te/test"
    directory.mkdir(parents=True)
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    monkeypatch.setattr(persistence_events, "_observer", None)

    class MetadataController(_DummyNoDb):
        filename = "ron.nodb"

    controller = MetadataController(str(directory))
    timings = {False: [], True: []}
    notification_timings = []
    observer = Adapter(Settings("postgres", "catalog"), roots, lambda: database)

    def measured_observer(event):
        started = time.perf_counter()
        observer(event)
        notification_timings.append(time.perf_counter() - started)

    baseline_observer = Adapter(Settings("postgres", "timestamp_only"), roots, lambda: database)
    for iteration in range(100):
        for enabled in ((False, True) if iteration % 2 == 0 else (True, False)):
            persistence_events.register_project_commit_observer(measured_observer if enabled else baseline_observer)
            started = time.perf_counter()
            with controller.locked(validate_on_success=False):
                controller._name = str(iteration)
            timings[enabled].append(time.perf_counter() - started)
    baseline_p95 = sorted(timings[False])[94]
    catalog_p95 = sorted(timings[True])[94]
    print(json.dumps({"timestamp_only_save_p95_seconds": baseline_p95, "save_catalog_p95_seconds": catalog_p95,
                      "p95_difference_seconds": catalog_p95 - baseline_p95,
                      "paired_delta_p95_seconds": sorted(new - old for new, old in zip(timings[True], timings[False]))[94],
                      "notification_p95_seconds": sorted(notification_timings)[94], "samples_per_mode": 100,
                      "baseline_seconds": timings[False], "catalog_seconds": timings[True]}))
    assert len(notification_timings) == 100
    assert catalog_p95 - baseline_p95 <= 0.05
    unavailable = sa.create_engine("postgresql://unused@127.0.0.1:1/unavailable", connect_args={"connect_timeout": 1}, hide_parameters=True)
    persistence_events.register_project_commit_observer(Adapter(Settings("postgres", "catalog"), roots, lambda: unavailable))
    started = time.perf_counter()
    try:
        with controller.locked(validate_on_success=False):
            controller._name = "saved despite database refusal"
    finally:
        unavailable.dispose()
    print(json.dumps({"database_refusal_save_seconds": time.perf_counter() - started}))
    assert "saved despite database refusal" in (directory / "ron.nodb").read_text()
    assert "project_commit_mirror_failed" in caplog.text


def test_reconciliation_reserves_capacity_under_dirty_traffic(database):
    from datetime import timedelta
    now = repository.utcnow()
    with database.begin() as connection:
        connection.execute(runs.insert(), [{"id": identifier, "runid": f"test-{identifier}"} for identifier in range(1, 51)])
        repository.seed(connection)
        connection.execute(catalog.update().values(next_reconcile_at=now + timedelta(hours=1)))
        connection.execute(catalog.update().where(catalog.c.run_id > 25).values(indexed_revision=1, next_reconcile_at=now - timedelta(hours=1)))
        selected = repository.candidates(connection, limit=20, now=now)
        assert len(selected) == 20
        assert len([identifier for identifier in selected if identifier > 25]) >= 5


@pytest.mark.parametrize("source", ["readonly", "ttl"])
@pytest.mark.slow
def test_marker_notification_latency_without_prior_sql_mirror(database, tmp_path, monkeypatch, source):
    import json
    import time
    from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
    from wepppy.nodb import base, persistence_events
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    from wepppy.weppcloud.utils.run_ttl import _write_payload
    register(database)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    directory = tmp_path / "te/test"
    directory.mkdir(parents=True)
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    monkeypatch.setattr(persistence_events, "_observer", None)
    monkeypatch.setattr(Roots, "from_environ", classmethod(lambda cls: roots))
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    controller = _DummyNoDb(str(directory))
    observer = Adapter(Settings("postgres", "catalog"), roots, lambda: database)
    timings = {False: [], True: []}
    for iteration in range(100):
        for enabled in ((False, True) if iteration % 2 == 0 else (True, False)):
            persistence_events.register_project_commit_observer(observer if enabled else None)
            marker_present = bool((iteration // 2) % 2)
            if source == "readonly":
                marker = directory / "READONLY"
                marker.unlink(missing_ok=True)
                if not marker_present:
                    marker.touch()
            started = time.perf_counter()
            if source == "readonly":
                controller.readonly = marker_present
            else:
                _write_payload(directory / "TTL", {"expires_at": "2030-01-01T00:00:00Z", "iteration": iteration})
            timings[enabled].append(time.perf_counter() - started)
    baseline_p95 = sorted(timings[False])[94]
    catalog_p95 = sorted(timings[True])[94]
    print(json.dumps({"source": source, "baseline_p95_seconds": baseline_p95, "catalog_p95_seconds": catalog_p95,
                      "p95_difference_seconds": catalog_p95 - baseline_p95, "samples_per_mode": 100,
                      "baseline_seconds": timings[False], "catalog_seconds": timings[True]}))
    assert catalog_p95 - baseline_p95 <= 0.05


@pytest.mark.slow
def test_timestamp_adapter_latency_against_legacy_helper(database, tmp_path, monkeypatch):
    import json
    import time
    from sqlalchemy.orm import Session
    from wepppy.nodb.persistence_events import ProjectCommit
    from wepppy.weppcloud import db_api
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    register(database)
    with database.connect() as connection:
        schema = connection.scalar(sa.text("SELECT current_schema()"))
    engines = []

    def legacy_session():
        engine = sa.create_engine(database.url, hide_parameters=True, connect_args={"options": "-csearch_path=" + schema})
        engines.append(engine)
        return Session(engine)

    monkeypatch.setattr(db_api, "_get_session", legacy_session)
    roots = Roots(primary=str(tmp_path))
    observer = Adapter(Settings("postgres", "timestamp_only"), roots, lambda: database)
    samples = {"legacy": [], "adapter": []}
    try:
        for iteration in range(100):
            for mode in (("legacy", "adapter") if iteration % 2 == 0 else ("adapter", "legacy")):
                committed = repository.utcnow()
                started = time.perf_counter()
                if mode == "legacy":
                    db_api.update_last_modified("test", committed.replace(tzinfo=None))
                else:
                    observer(ProjectCommit("test", str(tmp_path / "te/test"), "nodb", committed, "ron.nodb"))
                samples[mode].append(time.perf_counter() - started)
                while engines:
                    engines.pop().dispose()
    finally:
        for engine in engines:
            engine.dispose()
    legacy_p95, adapter_p95 = (sorted(samples[mode])[94] for mode in ("legacy", "adapter"))
    print(json.dumps({"source": "timestamp_helper", "legacy_p95_seconds": legacy_p95, "adapter_p95_seconds": adapter_p95,
                      "legacy_seconds": samples["legacy"], "adapter_seconds": samples["adapter"], "samples_per_mode": 100}))
    assert adapter_p95 - legacy_p95 <= 0.05


def test_per_run_lock_and_concurrent_deletion(database, tmp_path):
    from wepppy.weppcloud.run_catalog.extractor import extract
    register(database)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))

    def locked(runid, **kwargs):
        assert repository.refresh(database, 1, roots) == "busy"
        with database.begin() as connection:
            connection.execute(runs.delete().where(runs.c.id == 1))
        return extract(runid, **kwargs)

    assert repository.refresh(database, 1, roots, extractor=locked) == "discarded"
    with database.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(catalog)) == 0


@pytest.mark.parametrize("batch_name", ["omni", "omni-contrast"])
def test_grouped_adapter_preserves_parent_timestamp(database, tmp_path, batch_name):
    from datetime import datetime, timezone
    from wepppy.nodb.persistence_events import ProjectCommit
    from wepppy.weppcloud.run_catalog.adapter import Adapter, Settings
    parent = "batch;;" + batch_name + ";;leaf"
    child = parent + ";;omni;;burned"
    old = datetime(2000, 1, 1)
    with database.begin() as connection:
        connection.execute(runs.insert(), [{"id": identifier, "runid": runid, "last_modified": old}
                                           for identifier, runid in enumerate(("batch", parent, child), 1)])
        repository.seed(connection)
    roots = Roots(batch=str(tmp_path))
    observer = Adapter(Settings("postgres", "catalog"), roots, lambda: database)
    parent_path = tmp_path / batch_name / "runs" / "leaf"
    now = datetime.now(timezone.utc)
    observer(ProjectCommit(parent, str(parent_path), "nodb", now, "ron.nodb"))
    observer(ProjectCommit(child, str(parent_path / "_pups/omni/scenarios/burned"), "nodb", now, "ron.nodb"))
    with database.connect() as connection:
        timestamps = dict(connection.execute(sa.select(runs.c.runid, runs.c.last_modified)).all())
        assert timestamps == {"batch": old, parent: now.replace(tzinfo=None), child: old}
        assert list(connection.scalars(sa.select(catalog.c.dirty_revision).order_by(catalog.c.run_id))) == [1, 2, 2]


def test_real_migration_constraints_cascade(database):
    register(database)
    for policy in (None, "disabled", "unknown"):
        with pytest.raises(IntegrityError), database.begin() as connection:
            connection.execute(catalog.update().values(ttl_state="ready", ttl_policy=policy, ttl_deletion_at=repository.utcnow()))
    with database.begin() as connection:
        connection.execute(catalog.update().values(ttl_state="ready", ttl_policy="rolling_90d", ttl_deletion_at=repository.utcnow()))
        connection.execute(runs.delete())
        assert connection.scalar(sa.select(sa.func.count()).select_from(catalog)) == 0


@pytest.mark.parametrize("write_mode", ["catalog", "timestamp_only"])
def test_actual_registration_transaction_hook(database, monkeypatch, write_mode):
    from sqlalchemy.orm import Session
    from wepppy.weppcloud.app import Run
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", write_mode)
    with database.begin() as connection:
        connection.execute(sa.text("ALTER TABLE run ADD COLUMN bootstrap_disabled boolean NOT NULL DEFAULT false"))
    with Session(database) as session:
        session.add(Run(runid="rollback"))
        session.flush()
        assert session.scalar(sa.select(sa.func.count()).select_from(catalog)) == (1 if write_mode == "catalog" else 0)
        session.rollback()
        assert session.scalar(sa.select(sa.func.count()).select_from(catalog)) == 0
        session.add(Run(runid="committed"))
        session.commit()
    with database.connect() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(catalog)) == (1 if write_mode == "catalog" else 0)


def test_refresh_invalidation_and_offline_reconcile(database, tmp_path):
    register(database)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    project = tmp_path / "te" / "test"
    project.mkdir(parents=True)
    (project / "ron.nodb").write_text('{"_name":"first"}')
    assert repository.refresh(database, 1, roots) == "ready"
    with database.begin() as connection:
        row = connection.execute(sa.select(catalog)).mappings().one()
        assert row["name"] == "first"
        assert row["dirty_revision"] == row["indexed_revision"]
        repository.invalidate(connection, "test")
    (project / "ron.nodb").write_text('{"_name":"later"}')
    repository.refresh(database, 1, roots)
    with database.connect() as connection:
        assert connection.scalar(sa.select(catalog.c.name)) == "later"


def test_partial_ttl_failure_publishes_ron_clears_expiry(database, tmp_path):
    from wepppy.weppcloud.run_catalog.extractor import extract, Observation
    register(database)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    project = tmp_path / "te" / "test"
    project.mkdir(parents=True)
    (project / "ron.nodb").write_text('{"_name":"first"}')
    (project / "TTL").write_text('{"expires_at":"2030-01-01T00:00:00Z"}')
    repository.refresh(database, 1, roots)
    with database.connect() as connection:
        observed = connection.scalar(sa.select(catalog.c.ttl_observed_at))
    (project / "ron.nodb").write_text('{"_name":"changed"}')

    def failing(runid, **kwargs):
        snapshot = extract(runid, **kwargs)
        snapshot.sources["ttl"] = Observation("unreadable", error="source_io_error")
        return snapshot

    assert repository.refresh(database, 1, roots, extractor=failing) == "retry"
    with database.connect() as connection:
        row = connection.execute(sa.select(catalog)).mappings().one()
        assert row["name"] == "changed"
        assert row["ttl_deletion_at"] is None
        assert row["ttl_observed_at"] == observed
        assert row["dirty_revision"] > row["indexed_revision"]
    assert repository.refresh(database, 1, roots) == "ready"


def test_concurrent_invalidation_remains_dirty(database):
    from wepppy.weppcloud.run_catalog.extractor import Snapshot, Observation
    register(database)

    def concurrent(runid, **kwargs):
        with database.begin() as connection:
            repository.invalidate(connection, runid)
        return Snapshot(None, {source: Observation("missing" if source != "readonly" else "ready",
                                                   {"readonly": False} if source == "readonly" else {},
                                                   {"state": "missing"}) for source in ("ron", "readonly", "ttl")})

    assert repository.refresh(database, 1, extractor=concurrent) == "ready"
    with database.connect() as connection:
        row = connection.execute(sa.select(catalog)).mappings().one()
        assert row["dirty_revision"] == 2
        assert row["indexed_revision"] == 1


def test_replaced_projection_discards_obsolete_snapshot(database):
    from wepppy.weppcloud.run_catalog.extractor import Snapshot, Observation
    register(database)

    def replace_row(runid, **kwargs):
        with database.begin() as connection:
            connection.execute(catalog.delete())
            repository.seed(connection)
        return Snapshot(None, {source: Observation("missing" if source != "readonly" else "ready",
                                                   {"readonly": False} if source == "readonly" else {},
                                                   {"state": "missing"}) for source in ("ron", "readonly", "ttl")})

    assert repository.refresh(database, 1, extractor=replace_row) == "discarded"
    with database.connect() as connection:
        assert connection.scalar(sa.select(catalog.c.indexed_revision)) == 0


def test_failure_backoff_begins_after_slow_extraction(database, monkeypatch):
    from datetime import timedelta
    from wepppy.weppcloud.run_catalog.extractor import Snapshot, Observation
    register(database)
    started = repository.utcnow()
    finished = started + timedelta(seconds=90)
    clock = iter((started, finished))
    monkeypatch.setattr(repository, "utcnow", lambda: next(clock))

    def failed(runid, **kwargs):
        return Snapshot(None, {source: Observation("unreadable") for source in ("ron", "readonly", "ttl")})

    repository.refresh(database, 1, extractor=failed)
    with database.connect() as connection:
        row = connection.execute(sa.select(catalog)).mappings().one()
        assert row["next_attempt_at"] == finished + timedelta(seconds=60)
        assert row["next_reconcile_at"] == finished + timedelta(seconds=60)

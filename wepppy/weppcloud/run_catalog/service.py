"""Bounded catalog maintenance on existing PostgreSQL coordination."""

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timedelta
import threading
import time

import sqlalchemy as sa

from . import repository
from .schema import catalog, runs
from .extractor import extract

__all__ = ["sweep", "compare", "preflight", "probe_origin"]

OPERATOR_REQUIREMENTS = ("consumer_connection_bound_origin_proof", "live_producer_inventory", "source_mount_parity", "omission_manifest", "authorized_browser_parity", "browser_latency", "host_observation_window")


def probe_origin(connection, held_nonce, control_nonce):
    if held_nonce == control_nonce or any(type(value) is not int or not -(2 ** 63) <= value < 2 ** 63 for value in (held_nonce, control_nonce)):
        raise ValueError("Origin probe requires distinct signed-bigint nonces")
    held = connection.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(sa.cast(held_nonce, sa.BigInteger))))
    control = connection.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(sa.cast(control_nonce, sa.BigInteger))))
    return {"held_acquired": held, "control_acquired": control, "matches_origin": held is False and control is True}


def sweep(engine, roots=None, limit=50, run_id=None, apply=False, window=45):
    if not 1 <= limit <= 50:
        raise ValueError("Catalog limit must be between 1 and 50")
    started = time.monotonic()
    results = {}
    timings = {}
    with engine.begin() as coordinator:
        if not coordinator.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(1381322308, 0))):
            return {"state": "busy", "attempted": 0}
        if apply:
            with engine.begin() as connection:
                repository.seed(connection, limit=limit, run_id=run_id)
        selected = repository.candidates(coordinator, limit=limit) if run_id is None else list(coordinator.scalars(
            sa.select(catalog.c.run_id).where(catalog.c.run_id == run_id)))
        if not apply:
            return {"state": "dry_run", "run_ids": selected}
        coordination_lock = threading.Lock()

        def guard():
            with coordination_lock:
                coordinator.execute(sa.select(1))

        def refresh(identifier):
            guard()
            observed = {}
            outcome = repository.refresh(engine, identifier, roots, publication_guard=guard, metrics=observed)
            timings[identifier] = observed
            return outcome

        remaining = iter(selected)
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {}
            while True:
                while len(pending) < 2 and time.monotonic() - started < window:
                    identifier = next(remaining, None)
                    if identifier is None:
                        break
                    pending[pool.submit(refresh, identifier)] = identifier
                if not pending:
                    break
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in completed:
                    identifier = pending.pop(future)
                    results[identifier] = future.result()
    return {"state": "completed", "attempted": len(results), "outcomes": results,
            "failures": sum(outcome == "retry" for outcome in results.values()),
            "source_seconds": sum(value.get("source_seconds", 0) for value in timings.values()),
            "sql_acquire_seconds": sum(value.get("sql_acquire_seconds", 0) for value in timings.values()),
            "sql_publish_seconds": sum(value.get("sql_publish_seconds", 0) for value in timings.values()),
            "elapsed_seconds": time.monotonic() - started}


def compare(engine, roots=None, limit=50, run_id=None):
    if not 1 <= limit <= 50:
        raise ValueError("Catalog limit must be between 1 and 50")
    with engine.begin() as connection:
        if not connection.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(1381322308, 0))):
            return {"state": "busy"}
        query = sa.select(runs.c.runid, runs.c.id, catalog).outerjoin(catalog, runs.c.id == catalog.c.run_id)
        if run_id is not None:
            query = query.where(runs.c.id == run_id)
        reports = []
        for row in connection.execute(query.order_by(runs.c.id).limit(limit)).mappings():
            snapshot = extract(row["runid"], roots)
            mismatches = []
            unreadable = []
            for source, observation in snapshot.sources.items():
                if observation.state == "unreadable":
                    unreadable.append(source)
                if row[source + "_state"] != observation.state:
                    mismatches.append(source + "_state")
                for key, value in observation.values.items():
                    if row[key] != value:
                        mismatches.append(key)
            reports.append({"run_id": row["id"], "mismatches": mismatches, "unreadable_sources": unreadable,
                            "state": "inconclusive" if unreadable else "different" if mismatches else "match"})
        return {"state": "compared", "rows": reports}


def preflight(connection, settings, operational=None):
    observed = repository.status(connection)
    now = repository.utcnow()
    failures = []
    if settings.commit_mode != "postgres" or settings.write_mode != "catalog":
        failures.append("catalog_writes_disabled")
    if observed["registered"] != observed["projected"]:
        failures.append("projection_coverage")
    if observed["pending"] or observed["transient_failures"]:
        failures.append("source_observations_unresolved")
    if observed["registered"] and (observed["unreconciled"] or observed["oldest_reconciled_at"] is None or now - observed["oldest_reconciled_at"] > timedelta(hours=24)):
        failures.append("reconciliation_overdue")
    if observed["oldest_dirty_at"] and now - observed["oldest_dirty_at"] > timedelta(seconds=60):
        failures.append("notification_lag")
    operational = operational or {}
    if not operational.get("eligible_consumers") or operational.get("incompatible_consumers"):
        failures.append("consumer_configuration_unverified")
    health = operational.get("sweep", {})
    try:
        completed = datetime.fromisoformat(health["completed_at"])
        healthy = health.get("state") == "completed" and now - completed <= timedelta(seconds=60)
    except (KeyError, TypeError, ValueError):
        healthy = False
    if not healthy:
        failures.append("sweep_health_unverified")
    return {"technical_ready": not failures, "gate_status": "operator_evidence_required",
            "failures": failures, "observed": observed, "operational": operational,
            "promotion_requires": list(OPERATOR_REQUIREMENTS)}

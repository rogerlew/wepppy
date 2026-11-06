"""Read retained cycle coverage and raw artifacts; never author acceptance authority.

Run inside an existing production worker. Writes only a new private evidence file;
does not enqueue, pause, repair catalogs, acquire publication guards or generate
scientific outputs. The operator must review coverage before writing acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import time

import redis


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected an ISO timestamp or an explicit unknown")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).timestamp()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def raw(path):
    if path.is_symlink():
        raise ValueError("Metadata symlink is not permitted")
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def retained_snapshot(connection, key, dirty_key, ledger_key, maximum):
    """WATCH validates an SSCAN census without a Redis write or cleanup."""
    keys = [key, key + ":discovery", key + ":generation", key + ":scopes",
            key + ":frontier", key + ":stream", dirty_key, ledger_key]
    with connection.pipeline() as pipe:
        pipe.watch(*keys)
        cursor = json.loads(pipe.get(key) or "{}")
        discovery = json.loads(pipe.get(key + ":discovery") or "{}")
        ledger = json.loads(pipe.get(ledger_key) or "{}")
        populations = {}
        for name, member_key in (("cycle", key + ":scopes"), ("dirty", dirty_key)):
            if pipe.scard(member_key) > maximum:
                raise ValueError("Retained scope census exceeds explicit bound")
            members = set()
            scan = 0
            while True:
                scan, values = pipe.sscan(member_key, cursor=scan, count=500)
                members.update(value.decode() for value in values)
                if len(members) > maximum:
                    raise ValueError("Retained scope census exceeds explicit bound")
                if scan == 0:
                    break
            populations[name] = sorted(members)
        populations["pending"] = sorted({item["path"] for item in cursor.get("pending", [])})
        populations["admitted"] = sorted({item["scope"]["wd"] for item in ledger["jobs"].values()
                                           if item.get("scope")})
        result = {"cursor": cursor, "discovery": discovery, "populations": populations,
                  "frontier": pipe.llen(key + ":frontier"),
                  "stream": pipe.xlen(key + ":stream"),
                  "generation": (pipe.get(key + ":generation") or b"").decode()}
        pipe.multi()
        pipe.get(key + ":generation")
        pipe.execute()
        return result


def clean_cycle(snapshot, cycle):
    cursor, discovery = snapshot["cursor"], snapshot["discovery"]
    return bool(cursor.get("cycle") == cycle and discovery.get("cycle") == cycle
                and cursor.get("completed_at") and discovery.get("completed_at")
                and not snapshot["frontier"] and not snapshot["stream"]
                and not discovery.get("errors") and discovery.get("state") not in {"failed", "unavailable"}
                and not cursor.get("failures") and not cursor.get("cycle_errors")
                and not cursor.get("unavailable_namespaces") and not cursor.get("rediscovery_required")
                and not any(item.get("cycle") for item in cursor.get("pending", [])))


def scope_readback(locator, roots, cycle_started_at):
    from wepppy.query_engine import catalog_refresh as cr
    from wepppy.rq._query_catalog_inventory import validated_scope_path

    path = validated_scope_path(roots, locator)
    scope = cr.resolve_scope(path, create=False)
    if not scope.managed:
        raise ValueError("Retained scope is not managed")
    names = [path / cr.REFRESH_PATH / name for name in ("incarnation.json", "status.json")]
    names.append(path / "_query_engine/catalog.json")
    before = [raw(name) for name in names]
    status = json.loads(before[1]) if before[1] else {}
    catalog = json.loads(before[2]) if before[2] else None
    requests = cr.pending_catalog_requests(path)
    if scope.incarnation is None and any((path / cr.REFRESH_PATH / "requests").glob("*.json")):
        raise ValueError("Receipts exist without a current incarnation")
    receipts = [{"request_id": item["request_id"], "created_at": item.get("created_at"),
                 "created_epoch": timestamp(item.get("created_at"))} for item in requests]
    current = bool(status.get("state") == "current" and scope.incarnation
                   and status.get("incarnation") == scope.incarnation and before[2]
                   and status.get("catalog_digest") == digest(before[2]) and not requests)
    published_at = timestamp(status.get("updated_at")) if current else None
    # Queued/running updated_at is not last publication time. A retained published
    # attempt may prove that older time; absence remains unknown rather than zero.
    if published_at is None and status.get("publication_id"):
        identifier = status["publication_id"]
        if not isinstance(identifier, str) or Path(identifier).name != identifier:
            raise ValueError("Invalid publication identity")
        attempt_raw = raw(path / cr.REFRESH_PATH / "attempts" / (identifier + ".json"))
        attempt = json.loads(attempt_raw) if attempt_raw else {}
        if attempt.get("state") == "published" and attempt.get("incarnation") == scope.incarnation:
            published_at = timestamp(attempt.get("updated_at"))
    if catalog is not None:
        entries = catalog["files"]
        paths = [item["path"] for item in entries]
        if len(paths) != len(set(paths)) or any(cr.is_refresh_path(item) for item in paths):
            raise ValueError("Duplicate dataset or refresh metadata in catalog")
    if ([raw(name) for name in names] != before
            or cr.resolve_scope(path).directory_identity != scope.directory_identity
            or cr.pending_catalog_requests(path) != requests):
        raise ValueError("Scope changed during metadata readback")
    readonly = cr.is_catalog_readonly(path)
    return {"path": str(path), "scope_id": scope.scope_id, "namespace": scope.namespace,
            "incarnation": scope.incarnation, "directory_identity": scope.directory_identity,
            "relative_path": scope.relative_path, "readonly": readonly, "current": current,
            "catalog_sha256": digest(before[2]) if before[2] else None,
            "catalog_entries": len(catalog["files"]) if catalog is not None else None,
            "publication_at": published_at, "receipts": receipts,
            "published_during_cycle": bool(current and published_at is not None and published_at >= cycle_started_at),
            "checked_at": time.time()}


def artifact_readback(specification, roots, cycle_started_at):
    """Use the real pure planner/executor; bypass the potentially repairing barrier."""
    import pyarrow.parquet as pq
    from wepppy.query_engine import catalog_refresh as cr
    from wepppy.query_engine.catalog import DatasetCatalog
    from wepppy.query_engine.core import build_query_plan
    from wepppy.query_engine.executor import DuckDBExecutor
    from wepppy.query_engine.payload import QueryRequest

    before = scope_readback(specification["path"], roots, cycle_started_at)
    if before["readonly"] or not before["published_during_cycle"]:
        raise ValueError("Artifact sample must be a current writable cycle publication")
    path = Path(before["path"])
    datasets = specification["datasets"]
    if not datasets or len(datasets) > 16 or any(not name.endswith(".parquet") for name in datasets):
        raise ValueError("Supply one to sixteen explicit Parquet dataset keys")
    catalog_path = path / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_bytes())
    if not Path(catalog["root"]).samefile(path):
        raise ValueError("Catalog root does not identify sampled scope")
    cr._verify_required(path, catalog, datasets)
    queries = []
    for name in datasets:
        request = QueryRequest(datasets=[name], columns=[],
                               aggregations=[{"fn": "count", "column": "*", "alias": "n"}])
        plan = build_query_plan(request, DatasetCatalog.load(catalog_path))
        if plan.requires_spatial or len(plan.sources) != 1:
            raise ValueError("Expected one nonspatial Parquet source")
        source = Path(plan.sources[0].path)
        before_stat = source.stat()
        rows = pq.ParquetFile(source).metadata.num_rows
        result = DuckDBExecutor(path).execute(plan.sql, plan.params, sources=plan.sources)
        after_stat = source.stat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if result.to_pylist() != [{"n": rows}] or identity(after_stat) != identity(before_stat):
            raise ValueError("Query count mismatch or changing source")
        queries.append({"dataset": name, "rows": rows, "schema": str(pq.read_schema(source))})
    cr._verify_required(path, catalog, datasets)
    after = scope_readback(str(path), roots, cycle_started_at)
    if any(before[field] != after[field] for field in ("scope_id", "catalog_sha256", "publication_at", "receipts")):
        raise ValueError("Publication changed during artifact readback")
    return {"path": str(path), "namespace": before["namespace"], "queries": queries,
            "catalog_sha256": before["catalog_sha256"], "scope_id": before["scope_id"]}


def age_summary(rows, at):
    receipts = [receipt for row in rows for receipt in row["receipts"]]
    known = [receipt["created_epoch"] for receipt in receipts if receipt["created_epoch"] is not None]
    unresolved = [row for row in rows if not row["readonly"] and not row["current"]]
    older = [row["publication_at"] for row in unresolved if row["publication_at"] is not None]
    current = [row for row in rows if not row["readonly"] and row["current"]]
    current_dates = [row["publication_at"] for row in current if row["publication_at"] is not None]
    return {"as_of": at, "pending_receipts_observed": len(receipts),
            "pending_receipts_unknown_age": len(receipts) - len(known),
            "oldest_pending_receipt_created_at": min(known) if known else None,
            "oldest_pending_receipt_age_seconds": at - min(known) if known else None,
            "pending_or_noncurrent_writable_scopes": len(unresolved),
            "noncurrent_unknown_last_publication": len(unresolved) - len(older),
            "oldest_known_noncurrent_publication_age_seconds": at - min(older) if older else None,
            "current_publications_predating_cycle": sum(not row["published_during_cycle"] for row in current),
            "current_publications_unknown_age": len(current) - len(current_dates),
            "oldest_current_publication_age_seconds": at - min(current_dates) if current_dates else None,
            "readonly_scopes_exempt_from_generic_refresh": sum(row["readonly"] for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-seconds", type=int, default=1800)
    parser.add_argument("--maximum-scopes", type=int, default=100000)
    args = parser.parse_args()
    if (os.getuid(), os.getgid()) != (1002, 130) or os.getenv("EXTERNAL_HOST") != "wepp.cloud":
        raise ValueError("Expected production worker identity/environment")
    evidence = args.evidence
    if not evidence.is_absolute() or evidence.resolve() != evidence or evidence.stat().st_mode & 0o077:
        raise ValueError("Expected an existing private canonical evidence directory")
    if args.output.parent != evidence or args.output.exists() or not 1 <= args.maximum_seconds <= 172800:
        raise ValueError("Expected a fresh evidence output and bounded duration")
    manifest = json.loads((evidence / "manifest.json").read_text())
    target = json.loads((evidence / "target-cycle.json").read_text())
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    from wepppy.query_engine import catalog_refresh as cr
    from wepppy.rq import query_catalog_rq as cq, _query_catalog_admission as admission

    if manifest["expected_configuration"] != cq.catalog_worker_configuration() or not cr.catalog_refresh_enabled():
        raise ValueError("Observer and worker configuration differ")
    connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    identity = cq._configuration_id()
    key, dirty = "query-catalog:inventory:" + identity, "query-catalog:dirty:" + identity
    roots = cr.configured_roots()
    started = time.time()
    result = {"started_at": started, "cycle": target["cycle"], "status": "incomplete",
              "artifacts_verified": False, "pending_age_coverage_accepted": False,
              "scope_rows": [], "deleted_locators": [], "artifact_rows": [], "errors": []}

    def deadline(signum, frame):
        raise TimeoutError("Readback reached its explicit time bound")

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(args.maximum_seconds)
    try:
        before = retained_snapshot(connection, key, dirty, admission.LEDGER_KEY, args.maximum_scopes)
        cursor, discovery = before["cursor"], before["discovery"]
        if not clean_cycle(before, target["cycle"]):
            raise ValueError("Target cycle has not completed cleanly")
        paths = sorted(set().union(*(set(values) for values in before["populations"].values())))
        if len(paths) > args.maximum_scopes:
            raise ValueError("Union exceeds explicit scope bound")
        seen = {}
        for locator in paths:
            from wepppy.rq._query_catalog_inventory import InventoryScopeMissing
            try:
                row = scope_readback(locator, roots, cursor["cycle_started_at"])
            except InventoryScopeMissing:
                result["deleted_locators"].append({"path": locator, "checked_at": time.time()})
                continue
            if row["scope_id"] in seen:
                earlier = seen[row["scope_id"]]
                if any(earlier[field] != row[field] for field in
                       ("directory_identity", "incarnation", "catalog_sha256")):
                    raise ValueError("Alias identity/publication differs during census")
                seen[row["scope_id"]]["locators"].append(locator)
                continue
            row["locators"] = [locator]
            row["cycle_inventory_member"] = locator in before["populations"]["cycle"]
            seen[row["scope_id"]] = row
            result["scope_rows"].append(row)
        samples = json.loads(args.samples.read_text())
        if not samples or len(samples) > 32:
            raise ValueError("Expected one to thirty-two representative scopes")
        for spec in samples:
            if spec["path"] not in paths:
                raise ValueError("Artifact sample is outside the retained coverage union")
            result["artifact_rows"].append(artifact_readback(spec, roots, cursor["cycle_started_at"]))
        after = retained_snapshot(connection, key, dirty, admission.LEDGER_KEY, args.maximum_scopes)
        stable = (before["generation"] == after["generation"]
                  and before["populations"] == after["populations"]
                  and clean_cycle(after, target["cycle"]))
        result.update(status="readback_complete" if stable else "coverage_changed",
                      before=before, after=after, retained_membership_stable=stable,
                      locator_count=len(paths), unique_scope_count=len(seen),
                      duplicate_locators=len(paths) - len(seen) - len(result["deleted_locators"]),
                      namespaces=dict(Counter(row["namespace"] for row in seen.values())),
                      cycle_elapsed_seconds=cursor["completed_at"] - cursor["cycle_started_at"],
                      target_cycle_spacing_seconds=cursor.get("target_cycle_seconds"),
                      artifacts_verified=stable and len(result["artifact_rows"]) == len(samples))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, redis.RedisError) as exc:
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        signal.alarm(0)
        result["finished_at"] = time.time()
        result["ages"] = age_summary(result["scope_rows"], result["finished_at"])
        result["coverage_limit"] = "Retained target-cycle/dirty/pending/admitted union; interval census, not an atomic filesystem snapshot or discovery of later new scopes. Missing timestamps stay unknown. Artifact checks cover only listed samples."
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(result, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
    return 0 if result["status"] == "readback_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

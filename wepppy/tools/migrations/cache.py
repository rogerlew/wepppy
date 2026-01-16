"""Cache invalidation helpers for migrations."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

__all__ = ["invalidate_redis_cache"]


def invalidate_redis_cache(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Invalidate Redis DB 13 cache for all .nodb files in the working directory.

    NoDb instances are cached in Redis DB 13 with a 72-hour TTL. After migrations
    modify .nodb files on disk, the cache must be invalidated to prevent the
    Flask app from reading stale objects.

    Args:
        wd: Working directory path
        dry_run: If True, report what would be deleted but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    wd_abs = str(run_path.resolve())

    try:
        import redis
    except ImportError:
        return True, "Redis not available (cache invalidation skipped)"

    try:
        r = redis.Redis(host="redis", port=6379, db=13)
        r.ping()  # Verify connection
    except redis.ConnectionError:
        return True, "Redis not reachable (cache invalidation skipped)"
    except Exception as exc:
        return True, f"Redis connection failed: {exc} (cache invalidation skipped)"

    # Find all cached .nodb keys for this working directory
    pattern = f"{wd_abs}/*.nodb"
    keys = r.keys(pattern)

    if not keys:
        return True, "No cached .nodb files found in Redis"

    if dry_run:
        return True, f"Would invalidate {len(keys)} cached .nodb file(s) from Redis"

    # Delete all cached .nodb files
    deleted_count = 0
    for key in keys:
        try:
            r.delete(key)
            deleted_count += 1
        except Exception:
            pass  # Best effort

    return True, f"Invalidated {deleted_count} cached .nodb file(s) from Redis DB 13"

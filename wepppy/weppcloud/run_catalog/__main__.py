"""Operator-only catalog maintenance; mutations require --apply."""

import argparse
import json
import logging

from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from .adapter import get_engine, initialize
from .paths import Roots
from . import repository, service


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "seed", "refresh", "reconcile", "compare", "preflight"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--held-nonce", type=int)
    parser.add_argument("--control-nonce", type=int)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")
    if args.command == "refresh" and args.run_id is None:
        parser.error("refresh requires --run-id")
    if (args.held_nonce is None) != (args.control_nonce is None) or (args.held_nonce is not None and args.command != "preflight"):
        parser.error("origin probes require preflight and both --held-nonce and --control-nonce")
    settings = initialize()
    if settings.commit_mode != "postgres":
        parser.error("Catalog CLI requires explicit postgres integration")
    engine = get_engine(refresh=True)
    try:
        operational = None
        if args.command in {"status", "preflight"}:
            import redis
            from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
            from wepppy.rq.run_catalog_rq import operational_status
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
                operational = operational_status(connection)
        if args.command in {"refresh", "reconcile"}:
            payload = service.sweep(engine, Roots.from_environ(), args.limit, args.run_id, args.apply)
        elif args.command == "compare":
            payload = service.compare(engine, Roots.from_environ(), args.limit, args.run_id)
        else:
            with engine.begin() as connection:
                if args.command == "status":
                    payload = repository.status(connection)
                    payload["operational"] = operational
                elif args.command == "seed":
                    payload = {"apply": args.apply, "run_ids": repository.seed(connection, args.limit, args.run_id, args.apply)}
                else:
                    payload = service.preflight(connection, settings, operational)
                    if args.held_nonce is not None:
                        payload["origin_probe"] = service.probe_origin(connection, args.held_nonce, args.control_nonce)
                        if not payload["origin_probe"]["matches_origin"]:
                            payload["technical_ready"] = False
                            payload["failures"].append("origin_probe_failed")
        print(json.dumps(payload, default=str, indent=2))
        return 1 if payload.get("technical_ready") is False else 0
    except SQLAlchemyError:
        logging.getLogger(__name__).error("catalog_database_unavailable")
        print(json.dumps({"error": "catalog_database_unavailable", "technical_ready": False,
                          "gate_status": "operator_evidence_required", "promotion_requires": service.OPERATOR_REQUIREMENTS}))
        return 1
    except RedisError:
        logging.getLogger(__name__).error("catalog_queue_unavailable")
        print(json.dumps({"error": "catalog_queue_unavailable", "technical_ready": False,
                          "gate_status": "operator_evidence_required", "promotion_requires": service.OPERATOR_REQUIREMENTS}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Derive and validate Docker Compose deployment contracts.

The deploy shell script deliberately delegates JSON handling here so its build
and acceptance sets are executable contracts rather than duplicated shell
lists. Input is the JSON emitted by ``docker compose config --format json`` or
``docker compose ps --all --format json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from typing import Any


def _load_json_stream() -> Any:
    source = sys.stdin.read().strip()
    if not source:
        raise ValueError("expected JSON on stdin")
    try:
        return json.loads(source)
    except json.JSONDecodeError:
        return [json.loads(line) for line in source.splitlines() if line.strip()]


def derive_build_services(config: dict[str, Any], active: set[str]) -> list[str]:
    """Return one active build service for each distinct resulting image."""

    services = config.get("services")
    if not isinstance(services, dict):
        raise ValueError("Compose config has no services object")

    selected: list[str] = []
    image_indexes: dict[str, int] = {}
    image_builds: dict[str, str] = {}
    for name, service in services.items():
        if name not in active or not isinstance(service, dict) or "build" not in service:
            continue
        image = service.get("image")
        image_key = str(image) if image else f"service:{name}"
        build_key = json.dumps(service["build"], sort_keys=True, separators=(",", ":"))
        if image_key in image_indexes:
            if image_builds[image_key] != build_key:
                raise ValueError(
                    f"services producing image {image_key!r} have conflicting build definitions"
                )
            if name == "weppcloud":
                selected[image_indexes[image_key]] = name
            continue
        image_indexes[image_key] = len(selected)
        image_builds[image_key] = build_key
        selected.append(name)
    return selected


def derive_expected_services(config: dict[str, Any], active: set[str]) -> list[str]:
    """Return active services whose effective replica count is not zero."""

    services = config.get("services")
    if not isinstance(services, dict):
        raise ValueError("Compose config has no services object")
    selected: list[str] = []
    for name, service in services.items():
        if name not in active or not isinstance(service, dict):
            continue
        if name.endswith("-build"):
            continue
        deploy = service.get("deploy") or {}
        if isinstance(deploy, dict) and deploy.get("replicas") == 0:
            continue
        selected.append(name)
    return selected


def validate_ps(records: Iterable[dict[str, Any]], expected: set[str]) -> list[str]:
    """Return explicit errors for absent, stopped, or unhealthy services."""

    by_service: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        service = str(record.get("Service", ""))
        if service:
            by_service.setdefault(service, []).append(record)

    errors: list[str] = []
    for service in sorted(expected):
        instances = by_service.get(service, [])
        if not instances:
            errors.append(f"service {service!r} has no container")
            continue
        for instance in instances:
            name = instance.get("Name") or service
            state = str(instance.get("State", "")).lower()
            health = str(instance.get("Health", "")).lower()
            if state != "running":
                errors.append(f"container {name!r} state is {state or 'unknown'}, expected running")
            if health and health != "healthy":
                errors.append(f"container {name!r} health is {health}, expected healthy")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-services")
    build.add_argument("--active-service", action="append", default=[])

    expected = subparsers.add_parser("expected-services")
    expected.add_argument("--active-service", action="append", default=[])

    state = subparsers.add_parser("validate-ps")
    state.add_argument("--expected-service", action="append", default=[])

    images = subparsers.add_parser("candidate-images")
    images.add_argument("--expected-service", action="append", default=[])
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        payload = _load_json_stream()
        if args.command in {"build-services", "expected-services"}:
            if not isinstance(payload, dict):
                raise ValueError("Compose config must be one JSON object")
            if args.command == "build-services":
                services = derive_build_services(payload, set(args.active_service))
            else:
                services = derive_expected_services(payload, set(args.active_service))
            if not services:
                raise ValueError(f"effective topology produced no {args.command}")
            print("\n".join(services))
            return 0

        if args.command == "candidate-images":
            if not isinstance(payload, dict):
                raise ValueError("Compose config must be one JSON object")
            services = payload.get("services")
            if not isinstance(services, dict):
                raise ValueError("Compose config has no services object")
            for name in args.expected_service:
                service = services.get(name)
                if isinstance(service, dict) and "build" in service and service.get("image"):
                    print(f"{name}\t{service['image']}")
            return 0

        records = payload if isinstance(payload, list) else [payload]
        errors = validate_ps(records, set(args.expected_service))
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        return 0
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"compose deployment contract error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

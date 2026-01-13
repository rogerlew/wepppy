#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.weppcloud.utils.auth_tokens import JWTConfigurationError, JWTDecodeError, decode_token, get_jwt_config

MIN_TTL_SECONDS = 3600


def _load_token(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str | None:
    if args.token and args.token_file:
        parser.error("--token and --token-file are mutually exclusive")

    token = args.token
    if args.token_file:
        try:
            token = Path(args.token_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            parser.error(f"Unable to read token file: {exc}")
    if token:
        return token.strip()
    return None


def _decode_claims(
    token: str, audience: Sequence[str] | None, parser: argparse.ArgumentParser
) -> Mapping[str, Any]:
    try:
        return decode_token(token, audience=audience)
    except JWTConfigurationError as exc:
        parser.error(f"JWT configuration error: {exc}")
    except JWTDecodeError as exc:
        parser.error(f"Invalid token: {exc}")
    return {}


def _resolve_audience(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    return [value for value in values if value]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Revoke a JWT by writing its jti to the Redis denylist.",
    )
    parser.add_argument(
        "--token",
        help="JWT string to revoke (validated before inserting into the denylist)",
    )
    parser.add_argument(
        "--token-file",
        help="Read the JWT from a file instead of passing it on the command line",
    )
    parser.add_argument(
        "--jti",
        help="Token identifier to revoke (required if --token is not provided)",
    )
    parser.add_argument(
        "--expires-at",
        type=int,
        help="Epoch timestamp of token expiration (required when revoking by jti only)",
    )
    parser.add_argument(
        "--expires-in",
        type=int,
        help="TTL in seconds to use when revoking by jti only",
    )
    parser.add_argument(
        "--audience",
        "-a",
        action="append",
        help="Audience override used when validating the token",
    )
    parser.add_argument(
        "--subject",
        help="Optional subject value to store with the revocation record",
    )
    parser.add_argument(
        "--token-class",
        help="Optional token_class value to store with the revocation record",
    )
    parser.add_argument(
        "--reason",
        help="Optional reason stored with the revocation record",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the revocation payload as JSON",
    )

    args = parser.parse_args(argv)
    token = _load_token(args, parser)
    audience = _resolve_audience(args.audience)

    now = int(time.time())
    jti = args.jti
    exp: int | None = None
    subject = args.subject
    token_class = args.token_class

    if token:
        claims = _decode_claims(token, audience, parser)
        token_jti = claims.get("jti")
        if not token_jti:
            parser.error("Token missing jti claim")
        if jti and jti != token_jti:
            parser.error("Provided jti does not match token jti")
        jti = str(token_jti)
        exp_value = claims.get("exp")
        if exp_value is None:
            parser.error("Token missing exp claim")
        if not isinstance(exp_value, (int, float)):
            parser.error("Token exp claim must be numeric")
        exp = int(exp_value)
        token_sub = claims.get("sub")
        if token_sub is not None:
            if subject and subject != token_sub:
                parser.error("Provided subject does not match token subject")
            subject = str(token_sub)
        token_token_class = claims.get("token_class")
        if token_token_class is not None:
            if token_class and token_class != token_token_class:
                parser.error("Provided token_class does not match token token_class")
            token_class = str(token_token_class)
    else:
        if not jti:
            parser.error("Provide --token or --jti to revoke a token")
        if args.expires_at is not None:
            exp = args.expires_at
        elif args.expires_in is not None:
            exp = now + args.expires_in
        else:
            parser.error("Provide --expires-at or --expires-in when revoking by jti only")

    if exp is None:
        parser.error("Unable to determine token expiration time")

    leeway = get_jwt_config().leeway_seconds
    ttl = int(exp) - now + int(leeway)
    if ttl < MIN_TTL_SECONDS:
        ttl = MIN_TTL_SECONDS

    payload: dict[str, Any] = {
        "sub": subject,
        "token_class": token_class,
        "revoked_at": now,
        "exp": int(exp),
        "reason": args.reason,
    }
    key = f"auth:jwt:revoked:{jti}"

    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
        with redis.Redis(**conn_kwargs) as redis_conn:
            redis_conn.set(key, json.dumps(payload), ex=ttl)
    except Exception as exc:
        parser.error(f"Failed to write revocation to Redis: {exc}")

    output = {
        "jti": jti,
        "key": key,
        "ttl_seconds": ttl,
        "payload": payload,
    }
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Revoked jti={jti} (ttl={ttl}s)")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())

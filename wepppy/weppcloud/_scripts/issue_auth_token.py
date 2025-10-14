#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from wepppy.weppcloud.utils.auth_tokens import JWTConfigurationError, issue_token


def _parse_claims(pairs: list[str] | None) -> dict[str, str]:
    claims: dict[str, str] = {}
    if not pairs:
        return claims
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Claim '{item}' must be in key=value format")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("Claim keys cannot be empty")
        claims[key] = value
    return claims


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Issue a signed JWT for WEPPcloud services.",
    )
    parser.add_argument("subject", help="Subject of the token (typically a user or service identifier)")
    parser.add_argument(
        "--scope",
        "-s",
        action="append",
        help="Add a scope (can be specified multiple times)",
    )
    parser.add_argument(
        "--runs",
        help="Comma-separated list of run identifiers to embed in the token",
    )
    parser.add_argument(
        "--audience",
        "-a",
        action="append",
        help="Audience value; may be provided multiple times",
    )
    parser.add_argument(
        "--expires-in",
        type=int,
        help="Override token lifetime in seconds (defaults to WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS)",
    )
    parser.add_argument(
        "--claim",
        action="append",
        help="Additional claim in key=value form (can be provided multiple times)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output token and claims as pretty-printed JSON",
    )

    args = parser.parse_args(argv)

    try:
        extra_claims = _parse_claims(args.claim)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    runs = None
    if args.runs:

        runs = [item.strip() for item in args.runs.split(",") if item.strip()]

    try:
        result = issue_token(
            args.subject,
            scopes=args.scope,
            runs=runs,
            audience=args.audience,
            expires_in=args.expires_in,
            extra_claims=extra_claims,
        )
    except JWTConfigurationError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["token"])
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())

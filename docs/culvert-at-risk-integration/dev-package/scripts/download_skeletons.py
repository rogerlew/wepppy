#!/usr/bin/env python3
"""
Download the culvert batch skeleton archive from WEPPcloud.

This script is intentionally copy/paste-friendly for Culvert-at-Risk integration.

Download URL:
  https://{host}/weppcloud/culverts/{batch_uuid}/download/weppcloud_run_skeletons.zip

Auth:
  Use the *browse_token* returned by the submit/retry/finalize API responses:
    Authorization: Bearer <browse_token>

Usage:
  # With env vars (supports scripts/.env)
  WEPPCLOUD_HOST=wepp.cloud WEPPCLOUD_BROWSE_TOKEN=... \
    python download_skeletons.py --batch-uuid <uuid> --out /tmp/run_skeletons.zip

  # With explicit token argument
  python download_skeletons.py --batch-uuid <uuid> --browse-token <token>

Environment variables:
  WEPPCLOUD_HOST: Target host (no protocol prefix). Default: wepp.cloud
  WEPPCLOUD_BROWSE_TOKEN: browse_token JWT used for /weppcloud/culverts/* endpoints
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

DEFAULT_HOST = "wepp.cloud"
HOST_ENV_VAR = "WEPPCLOUD_HOST"
BROWSE_TOKEN_ENV_VAR = "WEPPCLOUD_BROWSE_TOKEN"
DOTENV_FILENAME = ".env"
SKELETONS_BASENAME = "weppcloud_run_skeletons.zip"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when the skeleton archive download fails."""


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _load_dotenv() -> None:
    """Load environment variables from a local scripts/.env file if present."""
    env_path = Path(__file__).resolve().parent / DOTENV_FILENAME
    if not env_path.exists():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Failed to read {env_path.name}: {exc}")
        return

    for line_num, raw in enumerate(content.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            logger.warning(f"Skipping invalid {env_path.name} entry on line {line_num}")
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            logger.warning(f"Skipping empty {env_path.name} key on line {line_num}")
            continue
        if key in os.environ:
            continue
        os.environ[key] = _strip_optional_quotes(value.strip())


def _build_base_url(host: str) -> str:
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    return f"https://{host}"


def build_skeletons_download_url(base_url: str, batch_uuid: str) -> str:
    """Build the canonical skeleton ZIP download URL for a batch UUID."""
    base_url = base_url.rstrip("/") + "/"
    rel = f"weppcloud/culverts/{batch_uuid}/download/{SKELETONS_BASENAME}"
    return urljoin(base_url, rel)


def download_run_skeletons_zip(
    *,
    base_url: str,
    batch_uuid: str,
    browse_token: str,
    out_path: Path,
    timeout_s: int = 3600,
    chunk_size: int = 1024 * 1024,
) -> Path:
    """
    Download `weppcloud_run_skeletons.zip` for batch_uuid to out_path.

    This is the reusable helper intended to be pulled into Culvert-at-Risk.
    """
    if not batch_uuid:
        raise DownloadError("batch_uuid is required")
    if not browse_token:
        raise DownloadError("browse_token is required")

    url = build_skeletons_download_url(base_url, batch_uuid)
    out_path = out_path.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")

    headers = {"Authorization": f"Bearer {browse_token}"}
    logger.info(f"Download target: {url}")
    logger.info(f"Output file: {out_path}")

    try:
        resp = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(30, timeout_s),
        )
    except requests.RequestException as exc:
        raise DownloadError(f"Request failed: {exc}") from exc

    if resp.status_code != 200:
        body_preview = ""
        try:
            body_preview = (resp.text or "").strip()
        except Exception:
            body_preview = ""
        if body_preview:
            body_preview = body_preview[:300]
            raise DownloadError(f"Download failed: HTTP {resp.status_code}: {body_preview}")
        raise DownloadError(f"Download failed: HTTP {resp.status_code}")

    wrote_bytes = 0
    try:
        with tmp_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                wrote_bytes += len(chunk)

        if wrote_bytes < 4:
            raise DownloadError(f"Downloaded file too small ({wrote_bytes} bytes)")

        with tmp_path.open("rb") as f:
            magic = f.read(4)
        if not magic.startswith(b"PK"):
            raise DownloadError(f"Downloaded file is not a ZIP (magic={magic!r})")

        os.replace(tmp_path, out_path)
        logger.info(f"Download complete: {wrote_bytes:,} bytes")
        return out_path
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download weppcloud_run_skeletons.zip for a culvert batch.",
    )
    parser.add_argument("--batch-uuid", required=True, help="Culvert batch UUID")
    parser.add_argument(
        "--host",
        default=None,
        help=f"WEPPcloud host (default: {HOST_ENV_VAR} env or {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--browse-token",
        default=None,
        help=f"Browse token (default: {BROWSE_TOKEN_ENV_VAR} env)",
    )
    parser.add_argument(
        "--browse-token-file",
        type=Path,
        default=None,
        help="Path to a file containing the browse token.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for weppcloud_run_skeletons.zip",
    )

    args = parser.parse_args()
    if args.browse_token and args.browse_token_file:
        parser.error("--browse-token and --browse-token-file are mutually exclusive")

    _load_dotenv()

    host = (args.host or os.getenv(HOST_ENV_VAR) or DEFAULT_HOST).strip()
    base_url = _build_base_url(host)

    browse_token: Optional[str] = None
    if args.browse_token_file:
        try:
            browse_token = args.browse_token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.error(f"Failed to read token file: {exc}")
            return 3
    elif args.browse_token:
        browse_token = args.browse_token.strip()
    else:
        browse_token = (os.getenv(BROWSE_TOKEN_ENV_VAR) or "").strip() or None

    try:
        download_run_skeletons_zip(
            base_url=base_url,
            batch_uuid=str(args.batch_uuid).strip(),
            browse_token=browse_token or "",
            out_path=args.out,
        )
        return 0
    except DownloadError as exc:
        logger.error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())


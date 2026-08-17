#!/usr/bin/env python3
"""Download WATAR (ash transport) results from a WEPPcloud batch.

This talks to the public WEPPcloud browse/download server over HTTPS. It needs
nothing but a stock Python 3.8+ interpreter -- no pip installs, no credentials,
no shell access to the modeling host. The runs in the NASA ROSES batches are
flagged PUBLIC, so anonymous access works.

Typical use
-----------

    # See which runs have ash results, download nothing
    python3 download_watar_results.py --list

    # Download just the watershed/hillslope summary tables (small, ~5 files/run)
    python3 download_watar_results.py --summary-only --out ./watar

    # Download everything under ash/ for every run (large: one parquet per
    # hillslope, plus PNG plots)
    python3 download_watar_results.py --out ./watar

    # A couple of runs only
    python3 download_watar_results.py --runs OR-60 WA-10 OR-6 --out ./watar

What gets downloaded
--------------------

Each run's ``ash/`` directory is mirrored to ``<out>/<run>/ash/...``. When WATAR
has been run, that directory holds:

    ash/post/hillslope_annuals.parquet
    ash/post/watershed_annuals.parquet
    ash/post/watershed_daily.parquet
    ash/post/watershed_daily_by_burn_class.parquet
    ash/post/watershed_cumulatives.parquet   <- the summary tables
    ash/H<wepp_id>_ash.parquet               <- one per hillslope (bulk)
    ash/H<wepp_id>_ash.png, *_ash_scatter.png
    ash/ash_load_cropped.tif, ash_bulk_density_cropped.tif, ash_type_map_cropped.tif

Runs whose ``ash/`` directory is missing or empty are reported as having no
results and are skipped. That is not an error -- it just means WATAR has not
been run for that watershed yet.

Two CSV reports are written into the output directory:

    runs_summary.csv   one row per run: file count, bytes, status
    manifest.csv       one row per file: run, path, url, bytes, status

Downloads are resumable in the coarse sense: a file that already exists locally
is skipped unless --overwrite is given. Partial transfers are written to a
``.part`` file and renamed only on success, so an interrupted run never leaves a
truncated file that looks complete.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import html
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_SITE = "https://wepp.cloud"
SITE_PREFIX = "/weppcloud"
DEFAULT_BATCH = "nasa-roses-202606-psbs"
DEFAULT_CONFIG = "disturbed9002-wbt-mofe"
DEFAULT_SUBDIR = "ash"

# The browse server paginates directory listings at 100 entries per page
# (MAX_FILE_LIMIT in wepppy/microservices/browse/listing.py).
PAGE_SIZE = 100

USER_AGENT = "wepppy-watar-downloader/1.0"

_HREF_RE = re.compile(r'href="([^"]*)"')
_SHOWING_RE = re.compile(r"Showing items\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)")
_NO_ITEMS_RE = re.compile(r"No items to display")
# Row shape: ... <a href=".../browse/<dir>/<name>">name  </a>2026-07-07 08:26    974.7 KB ...
_SIZE_RE = re.compile(r"</a>\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+([\d.]+\s*[KMGTP]?B|\d+)\s")


class FatalError(RuntimeError):
    """Unrecoverable problem; abort with a readable message."""


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


class BrowseClient:
    """Minimal HTTP client for the WEPPcloud browse/download routes."""

    def __init__(
        self,
        site: str = DEFAULT_SITE,
        token: Optional[str] = None,
        timeout: float = 300.0,
        retries: int = 3,
        retry_wait: float = 2.0,
    ) -> None:
        self.site = site.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.retries = max(1, retries)
        self.retry_wait = retry_wait

    def _request(self, url: str) -> urllib.request.Request:
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if self.token:
            headers["Authorization"] = "Bearer %s" % self.token
        return urllib.request.Request(url, headers=headers)

    def _open(self, url: str):
        """Open a URL with bounded retries. Raises HTTPError for 4xx."""
        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.retries + 1):
            try:
                return urllib.request.urlopen(self._request(url), timeout=self.timeout)
            except urllib.error.HTTPError as exc:
                # 4xx are answers, not transport failures -- do not retry them.
                if 400 <= exc.code < 500:
                    raise
                last_exc = exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
            if attempt < self.retries:
                time.sleep(self.retry_wait * attempt)
        raise FatalError("GET %s failed after %d attempts: %s" % (url, self.retries, last_exc))

    def get_text(self, url: str) -> str:
        with self._open(url) as resp:
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")

    def download(self, url: str, dest: str) -> int:
        """Stream a URL to dest via a .part file. Returns bytes written."""
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        part = dest + ".part"
        total = 0
        try:
            with self._open(url) as resp, open(part, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    total += len(chunk)
            os.replace(part, dest)
        except BaseException:
            if os.path.exists(part):
                try:
                    os.remove(part)
                except OSError:
                    pass
            raise
        return total


# --------------------------------------------------------------------------
# URL construction
# --------------------------------------------------------------------------


def composite_runid(batch: str, run: str) -> str:
    """WEPPcloud addresses a batch leaf run as ``batch;;<batch>;;<run>``."""
    return "batch;;%s;;%s" % (batch, run)


def run_browse_url(site: str, runid: str, config: str, rel: str) -> str:
    enc_runid = urllib.parse.quote(runid, safe="")
    enc_config = urllib.parse.quote(config, safe="")
    enc_rel = urllib.parse.quote(rel.strip("/"), safe="/")
    tail = enc_rel + "/" if enc_rel else ""
    return "%s%s/runs/%s/%s/browse/%s" % (site, SITE_PREFIX, enc_runid, enc_config, tail)


def run_download_url(site: str, runid: str, config: str, rel: str) -> str:
    enc_runid = urllib.parse.quote(runid, safe="")
    enc_config = urllib.parse.quote(config, safe="")
    enc_rel = urllib.parse.quote(rel.lstrip("/"), safe="/")
    return "%s%s/runs/%s/%s/download/%s" % (site, SITE_PREFIX, enc_runid, enc_config, enc_rel)


def batch_browse_url(site: str, batch: str, rel: str) -> str:
    enc_batch = urllib.parse.quote(batch, safe="")
    enc_rel = urllib.parse.quote(rel.strip("/"), safe="/")
    tail = enc_rel + "/" if enc_rel else ""
    return "%s%s/batch/%s/browse/%s" % (site, SITE_PREFIX, enc_batch, tail)


# --------------------------------------------------------------------------
# HTML listing parser
#
# The browse server renders directory listings as a <pre> block of anchor tags.
# Filenames are interpolated raw (no percent-encoding, no HTML escaping), so the
# hrefs can be matched against an unencoded prefix and sliced directly.
# --------------------------------------------------------------------------


def _page_count(page_html: str) -> int:
    if _NO_ITEMS_RE.search(page_html):
        return 0
    match = _SHOWING_RE.search(page_html)
    if not match:
        # No pagination banner: assume a single page rather than looping.
        return 1
    total_items = int(match.group(3))
    return max(1, math.ceil(total_items / PAGE_SIZE))


def _parse_entries(
    page_html: str,
    browse_prefix: str,
    download_prefix: Optional[str],
    rel: str,
) -> Tuple[List[str], List[str]]:
    """Return (file_rel_paths, dir_rel_paths) for direct children of ``rel``."""
    rel = rel.strip("/")
    parent = rel + "/" if rel else ""
    files: List[str] = []
    dirs: List[str] = []
    seen_files = set()
    seen_dirs = set()

    for raw_href in _HREF_RE.findall(page_html):
        href = html.unescape(raw_href)
        # Drop query strings (?sort=, ?page=, ?as_csv=1, ?pqf=...); the bare
        # path is what identifies the entry.
        path = href.split("?", 1)[0]

        if download_prefix and path.startswith(download_prefix):
            child = path[len(download_prefix):]
            if not child or child.endswith("/"):
                continue
            if os.path.dirname(child) != rel:
                continue
            if child not in seen_files:
                seen_files.add(child)
                files.append(child)
            continue

        if path.startswith(browse_prefix):
            child = path[len(browse_prefix):]
            if not child.endswith("/"):
                continue
            child = child.rstrip("/")
            if not child:
                continue
            # Direct child directories only -- skips breadcrumbs and self links.
            if os.path.dirname(child) != rel:
                continue
            if child not in seen_dirs:
                seen_dirs.add(child)
                dirs.append(child)

    # A directory listing with no download links (e.g. the batch runs/ index)
    # yields dirs only; that is expected.
    _ = parent
    return files, dirs


def _list_paginated(
    client: BrowseClient,
    base_url: str,
    browse_prefix: str,
    download_prefix: Optional[str],
    rel: str,
) -> Tuple[List[str], List[str]]:
    first = client.get_text(base_url)
    pages = _page_count(first)
    if pages == 0:
        return [], []

    files, dirs = _parse_entries(first, browse_prefix, download_prefix, rel)
    for page in range(2, pages + 1):
        sep = "&" if "?" in base_url else "?"
        page_html = client.get_text("%s%spage=%d" % (base_url, sep, page))
        more_files, more_dirs = _parse_entries(page_html, browse_prefix, download_prefix, rel)
        files.extend(f for f in more_files if f not in files)
        dirs.extend(d for d in more_dirs if d not in dirs)
    return files, dirs


def list_batch_runs(client: BrowseClient, batch: str) -> List[str]:
    """Enumerate leaf run names from the batch-level browse index."""
    url = batch_browse_url(client.site, batch, "runs")
    browse_prefix = "%s/batch/%s/browse/" % (SITE_PREFIX, batch)
    try:
        _files, dirs = _list_paginated(client, url, browse_prefix, None, "runs")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise FatalError(
                "Batch index %s is not publicly readable (HTTP %d). Pass --runs "
                "with explicit run names, or --token with a bearer token." % (url, exc.code)
            )
        if exc.code == 404:
            raise FatalError("Batch %r not found at %s" % (batch, url))
        raise
    return sorted(d.split("/", 1)[1] for d in dirs if d.startswith("runs/"))


def walk_run_dir(
    client: BrowseClient,
    runid: str,
    config: str,
    root: str,
) -> List[str]:
    """Recursively list files under ``root`` in a run. Returns run-relative paths."""
    browse_prefix = "%s/runs/%s/%s/browse/" % (SITE_PREFIX, runid, config)
    download_prefix = "%s/runs/%s/%s/download/" % (SITE_PREFIX, runid, config)

    collected: List[str] = []
    pending = [root.strip("/")]
    while pending:
        rel = pending.pop(0)
        url = run_browse_url(client.site, runid, config, rel)
        try:
            files, dirs = _list_paginated(client, url, browse_prefix, download_prefix, rel)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # Directory does not exist for this run.
                continue
            if exc.code in (401, 403):
                raise FatalError(
                    "Run %r is not publicly readable (HTTP %d at %s). Pass --token "
                    "with a bearer token." % (runid, exc.code, url)
                )
            raise
        collected.extend(files)
        pending.extend(dirs)
    return sorted(collected)


# --------------------------------------------------------------------------
# Selection + orchestration
# --------------------------------------------------------------------------


@dataclass
class RunResult:
    run: str
    n_listed: int = 0
    n_selected: int = 0
    n_downloaded: int = 0
    n_skipped: int = 0
    n_failed: int = 0
    bytes_downloaded: int = 0
    status: str = "no-results"
    note: str = ""
    rows: List[Dict[str, object]] = field(default_factory=list)


def _selected(path: str, includes: Sequence[str], excludes: Sequence[str]) -> bool:
    if includes and not any(fnmatch.fnmatch(path, pat) for pat in includes):
        return False
    if excludes and any(fnmatch.fnmatch(path, pat) for pat in excludes):
        return False
    return True


def process_run(
    client: BrowseClient,
    batch: str,
    run: str,
    config: str,
    subdir: str,
    out_dir: str,
    includes: Sequence[str],
    excludes: Sequence[str],
    overwrite: bool,
    dry_run: bool,
    list_only: bool,
) -> RunResult:
    result = RunResult(run=run)
    runid = composite_runid(batch, run)

    try:
        listed = walk_run_dir(client, runid, config, subdir)
    except FatalError:
        raise
    except urllib.error.HTTPError as exc:
        result.status = "error"
        result.note = "HTTP %d listing %s/" % (exc.code, subdir)
        return result

    result.n_listed = len(listed)
    if not listed:
        result.status = "no-results"
        result.note = "%s/ is missing or empty" % subdir
        return result

    selected = [p for p in listed if _selected(p, includes, excludes)]
    result.n_selected = len(selected)
    result.status = "has-results"

    if list_only:
        return result

    run_out = os.path.join(out_dir, run)
    for rel in selected:
        url = run_download_url(client.site, runid, config, rel)
        dest = os.path.join(run_out, *rel.split("/"))
        row: Dict[str, object] = {
            "run": run,
            "path": rel,
            "url": url,
            "bytes": "",
            "status": "",
        }

        if dry_run:
            row["status"] = "dry-run"
            result.rows.append(row)
            continue

        if os.path.exists(dest) and not overwrite:
            row["status"] = "skipped-exists"
            row["bytes"] = os.path.getsize(dest)
            result.n_skipped += 1
            result.rows.append(row)
            continue

        try:
            nbytes = client.download(url, dest)
        except (urllib.error.HTTPError, FatalError, OSError) as exc:
            row["status"] = "failed: %s" % exc
            result.n_failed += 1
            result.rows.append(row)
            continue

        row["status"] = "downloaded"
        row["bytes"] = nbytes
        result.n_downloaded += 1
        result.bytes_downloaded += nbytes
        result.rows.append(row)

    if result.n_failed:
        result.status = "partial"
    return result


def human_bytes(n: int) -> str:
    step = 1024.0
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < step or unit == "TB":
            return "%.1f %s" % (value, unit) if unit != "B" else "%d B" % int(value)
        value /= step
    return "%.1f TB" % value


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download WATAR (ash transport) results from a WEPPcloud batch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --list\n"
            "  %(prog)s --summary-only --out ./watar\n"
            "  %(prog)s --runs OR-60 WA-10 --out ./watar\n"
        ),
    )
    parser.add_argument("--batch", default=DEFAULT_BATCH, help="batch name (default: %(default)s)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="run config slug (default: %(default)s)")
    parser.add_argument("--site", default=DEFAULT_SITE, help="WEPPcloud site root (default: %(default)s)")
    parser.add_argument("--out", default="./watar_results", help="output directory (default: %(default)s)")
    parser.add_argument(
        "--subdir",
        default=DEFAULT_SUBDIR,
        help="run-relative directory to mirror (default: %(default)s)",
    )
    parser.add_argument(
        "--runs",
        nargs="+",
        metavar="RUN",
        help="explicit run names; default is every run in the batch",
    )
    parser.add_argument("--runs-file", help="file with one run name per line")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="download only the ash/post/*.parquet summary tables",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="only download run-relative paths matching this glob (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip run-relative paths matching this glob (repeatable)",
    )
    parser.add_argument("--jobs", type=int, default=4, help="concurrent runs (default: %(default)s)")
    parser.add_argument("--limit", type=int, help="process at most N runs (useful for a smoke test)")
    parser.add_argument("--overwrite", action="store_true", help="re-download files that already exist")
    parser.add_argument("--dry-run", action="store_true", help="list what would be downloaded, transfer nothing")
    parser.add_argument("--list", dest="list_only", action="store_true",
                        help="report which runs have results, transfer nothing")
    parser.add_argument("--token", help="bearer token (only needed for non-public runs)")
    parser.add_argument("--timeout", type=float, default=300.0, help="per-request timeout, seconds")
    parser.add_argument("--retries", type=int, default=3, help="retries per request (default: %(default)s)")
    return parser


def resolve_runs(client: BrowseClient, args: argparse.Namespace) -> List[str]:
    runs: List[str] = []
    if args.runs:
        runs.extend(args.runs)
    if args.runs_file:
        with open(args.runs_file) as fh:
            runs.extend(line.strip() for line in fh if line.strip() and not line.startswith("#"))
    if not runs:
        print("Enumerating runs in batch %r ..." % args.batch, flush=True)
        runs = list_batch_runs(client, args.batch)
    # Preserve order, drop duplicates.
    seen = set()
    ordered = [r for r in runs if not (r in seen or seen.add(r))]
    if args.limit:
        ordered = ordered[: args.limit]
    return ordered


def write_reports(out_dir: str, results: Sequence[RunResult]) -> Tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, "runs_summary.csv")
    manifest_path = os.path.join(out_dir, "manifest.csv")

    with open(summary_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["run", "status", "files_listed", "files_selected", "downloaded",
             "skipped", "failed", "bytes_downloaded", "note"]
        )
        for r in results:
            writer.writerow(
                [r.run, r.status, r.n_listed, r.n_selected, r.n_downloaded,
                 r.n_skipped, r.n_failed, r.bytes_downloaded, r.note]
            )

    with open(manifest_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["run", "path", "url", "bytes", "status"])
        writer.writeheader()
        for r in results:
            for row in r.rows:
                writer.writerow(row)

    return summary_path, manifest_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    includes = list(args.include)
    if args.summary_only:
        includes.append("%s/post/*.parquet" % args.subdir.strip("/"))

    client = BrowseClient(
        site=args.site,
        token=args.token,
        timeout=args.timeout,
        retries=args.retries,
    )

    try:
        runs = resolve_runs(client, args)
    except FatalError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if not runs:
        print("error: no runs to process", file=sys.stderr)
        return 2

    out_dir = os.path.abspath(args.out)
    mode = "list" if args.list_only else ("dry-run" if args.dry_run else "download")
    print(
        "batch=%s  runs=%d  subdir=%s/  mode=%s  out=%s"
        % (args.batch, len(runs), args.subdir.strip("/"), mode, out_dir),
        flush=True,
    )
    if includes:
        print("include: %s" % ", ".join(includes), flush=True)
    if args.exclude:
        print("exclude: %s" % ", ".join(args.exclude), flush=True)
    print("", flush=True)

    results: List[RunResult] = []
    jobs = max(1, args.jobs)
    fatal: Optional[BaseException] = None

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                process_run,
                client,
                args.batch,
                run,
                args.config,
                args.subdir,
                out_dir,
                includes,
                args.exclude,
                args.overwrite,
                args.dry_run,
                args.list_only,
            ): run
            for run in runs
        }
        for done, future in enumerate(as_completed(futures), start=1):
            run = futures[future]
            try:
                result = future.result()
            except FatalError as exc:
                fatal = exc
                result = RunResult(run=run, status="error", note=str(exc))
            except Exception as exc:  # keep going; the run is reported as failed
                result = RunResult(run=run, status="error", note=repr(exc))
            results.append(result)

            if result.status == "no-results":
                detail = result.note
            elif result.status == "error":
                detail = result.note
            elif args.list_only:
                detail = "%d files" % result.n_listed
            elif args.dry_run:
                detail = "%d/%d files selected" % (result.n_selected, result.n_listed)
            else:
                detail = "%d downloaded, %d skipped, %d failed, %s" % (
                    result.n_downloaded,
                    result.n_skipped,
                    result.n_failed,
                    human_bytes(result.bytes_downloaded),
                )
            print("[%3d/%3d] %-12s %-12s %s" % (done, len(runs), run, result.status, detail), flush=True)

    results.sort(key=lambda r: r.run)
    summary_path, manifest_path = write_reports(out_dir, results)

    with_results = [r for r in results if r.status in ("has-results", "partial")]
    errored = [r for r in results if r.status == "error"]
    total_bytes = sum(r.bytes_downloaded for r in results)
    total_files = sum(r.n_downloaded for r in results)
    total_failed = sum(r.n_failed for r in results)

    print("")
    print("=" * 68)
    print("runs with %s/ results : %d of %d" % (args.subdir.strip("/"), len(with_results), len(results)))
    print("runs with no results   : %d" % (len(results) - len(with_results) - len(errored)))
    if errored:
        print("runs with errors       : %d" % len(errored))
    if not (args.list_only or args.dry_run):
        print("files downloaded       : %d (%s)" % (total_files, human_bytes(total_bytes)))
        if total_failed:
            print("files failed           : %d" % total_failed)
    print("summary  : %s" % summary_path)
    print("manifest : %s" % manifest_path)
    print("=" * 68)

    if fatal is not None:
        print("\nerror: %s" % fatal, file=sys.stderr)
        return 2
    if errored or total_failed:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        sys.exit(130)

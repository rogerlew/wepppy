import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]


def _extract_caddy_regex(caddyfile: Path, matcher_name: str) -> tuple[int, re.Pattern[str]]:
    lines = caddyfile.read_text().splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        marker = f"path_regexp {matcher_name} "
        if marker in stripped:
            regex = stripped.split(marker, 1)[1]
            return index, re.compile(regex)
    raise AssertionError(f"{matcher_name} matcher missing from {caddyfile}")


@pytest.mark.parametrize(
    "relative_path",
    [
        "docker/caddy/Caddyfile",
        "docker/caddy/Caddyfile.wepp1",
    ],
)
def test_archive_download_caddy_matcher_precedes_browse_matcher(relative_path: str) -> None:
    caddyfile = REPO_ROOT / relative_path

    archive_index, archive_regex = _extract_caddy_regex(caddyfile, "archive_download_proxy")
    browse_index, browse_regex = _extract_caddy_regex(caddyfile, "browse_proxy")

    assert archive_index < browse_index
    assert archive_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/archives/run.zip")
    assert archive_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/archives/run.ZIP")
    assert archive_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/archives/nested/run.zip")
    assert not archive_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/archives/run.txt")
    assert not archive_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/output/run.zip")
    assert not archive_regex.fullmatch("/weppcloud/culverts/c1/download/archives/run.zip")

    assert browse_regex.fullmatch("/weppcloud/runs/run-1/cfg/download/output/run.zip")
    assert browse_regex.fullmatch("/weppcloud/runs/run-1/cfg/schema/output/table.parquet")


@pytest.mark.parametrize(
    "relative_path",
    [
        "docker/docker-compose.dev.yml",
        "docker/docker-compose.prod.yml",
        "docker/docker-compose.prod.wepp1.yml",
    ],
)
def test_compose_defines_dedicated_download_service(relative_path: str) -> None:
    compose_text = (REPO_ROOT / relative_path).read_text()

    assert "\n  download:" in compose_text
    assert "wepppy.microservices.download:app" in compose_text
    assert "0.0.0.0:9011" in compose_text

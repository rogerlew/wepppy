import pytest

from wepppy.nodir.paths import normalize_relpath, parse_external_subpath

pytestmark = pytest.mark.unit


def test_normalize_relpath_converts_backslashes() -> None:
    assert normalize_relpath(r"watershed\\a\\b") == "watershed/a/b"


@pytest.mark.parametrize(
    "raw",
    [
        "C:/a",
        "/C:/a",
        "./C:/a",
        "/./C:/a",
        r"/c:\a",
    ],
)
def test_normalize_relpath_rejects_windows_drive_letter(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_relpath(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "../a",
        "a/../b",
        "a/../../b",
        r"a\\..\\b",
    ],
)
def test_normalize_relpath_rejects_traversal(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_relpath(raw)


def test_parse_external_subpath_archive_boundary_allowlisted() -> None:
    rel, view = parse_external_subpath("watershed.nodir/a/b", allow_admin_alias=False)
    assert rel == "watershed/a/b"
    assert view == "archive"


def test_parse_external_subpath_watershed_nodir_is_not_boundary_without_trailing_slash() -> None:
    rel, view = parse_external_subpath("watershed.nodir", allow_admin_alias=False)
    assert rel == "watershed.nodir"
    assert view == "effective"


def test_parse_external_subpath_watershed_nodir_trailing_slash_enters_archive_root() -> None:
    rel, view = parse_external_subpath("watershed.nodir/", allow_admin_alias=False)
    assert rel == "watershed"
    assert view == "archive"


def test_parse_external_subpath_archive_boundary_non_allowlisted() -> None:
    rel, view = parse_external_subpath("foo.nodir/a", allow_admin_alias=False)
    assert rel == "foo.nodir/a"
    assert view == "effective"


def test_parse_external_subpath_admin_alias_requires_flag() -> None:
    rel, view = parse_external_subpath("watershed/nodir/a", allow_admin_alias=False)
    assert rel == "watershed/nodir/a"
    assert view == "effective"

    rel, view = parse_external_subpath("watershed/nodir/a", allow_admin_alias=True)
    assert rel == "watershed/a"
    assert view == "archive"

"""Locate legacy metadata without discarding an in-band PASS version marker."""

__all__ = ["pass_metadata_offset"]


def pass_metadata_offset(first_line: str) -> int:
    """Return the metadata offset, rejecting unsupported component versions."""
    marker = first_line.rstrip("\r\n")
    if marker == "WEPP_PASS_COMPONENTS 3":
        return 1
    if "WEPP_PASS_COMPONENTS" in marker:
        raise ValueError(f"Unsupported PASS components marker: {marker!r}")
    return 0

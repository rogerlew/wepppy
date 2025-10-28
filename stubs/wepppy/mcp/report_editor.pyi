from typing import Any, Dict, List, Mapping


def list_report_sections(runid: str, report_id: str, _jwt_claims: Mapping[str, Any] | None = ...) -> List[Dict[str, Any]]: ...

def read_report_section(runid: str, report_id: str, heading_pattern: str, _jwt_claims: Mapping[str, Any] | None = ...) -> str: ...

def replace_report_section(
    runid: str,
    report_id: str,
    heading_pattern: str,
    new_content: str,
    *,
    keep_heading: bool = ...,
    _jwt_claims: Mapping[str, Any] | None = ...,
) -> Dict[str, Any]: ...


"""Repository-only published evidence checks; no private fixture or model run."""
from dataclasses import asdict
import json
import pytest

from tests.roads.extract_fixture import digest
from tests.roads.roads_analysis import REPO, SUITE, source_hashes
from tests.roads.roads_matrix import CASES
from tests.roads.roads_report import render

pytestmark = pytest.mark.unit


def test_published_results_and_sources_are_current():
    provenance = json.loads((SUITE / "analysis_provenance_current.json").read_text())
    result = SUITE / "matrix_results_current.json"
    report = SUITE / "analysis_results_current.md"
    assert provenance["source_sha256"] == source_hashes(), "Sources changed: rerun/review Roads validation"
    assert digest(result) == provenance["results_sha256"]
    assert digest(report) == provenance["report_sha256"]
    payload = json.loads(result.read_text())
    assert [r["case"] for r in payload["cases"]] == [asdict(c) for c in CASES]
    assert len(provenance["case_artifacts"]) == len(CASES)
    assert provenance["native_sha256"]
    assert report.read_text() == render(payload["cases"], payload["projects"], provenance)


def test_usersum_vendor_identity_and_navigation():
    import yaml
    root = REPO / "wepppy/weppcloud/routes/usersum"
    vendor = root / "vendor/wepppy-roads/tests/roads/analysis_results_current.md"
    assert vendor.read_bytes() == (SUITE / "analysis_results_current.md").read_bytes()
    documents = yaml.safe_load((root / "docs_manifest.yaml").read_text())["docs"]
    document = next(d for d in documents if d["doc_id"] == "usersum.source.roads_validation")
    assert document["source"] == "vendor" and document["vendor_id"] == "wepppy-roads"
    assert document["min_role"] == "user"
    nav = (root / "nav_tree.yaml").read_text()
    assert nav.index("title: Workflows and Modules") < nav.index("doc_id: usersum.source.roads_validation")
    guide = (root / "weppcloud/models/roads/ENDUSER.md").read_text()
    assert "../../../vendor/wepppy-roads/tests/roads/analysis_results_current.md" in guide


def test_zero_detachment_contrasts_are_unavailable():
    payload = json.loads((SUITE / "matrix_results_current.json").read_text())
    provenance = json.loads((SUITE / "analysis_provenance_current.json").read_text())
    for row in payload["cases"]:
        row["summary"]["soil_loss_kg"] = 0.
        row["summary"]["soil_loss_density_kg_m2"] = 0.
    text = render(payload["cases"], payload["projects"], provenance)
    contrast = text.split("## Paired surface and traffic contrasts")[1].split("## One-factor")[0]
    assert contrast.count("| — | — | — |") == 3

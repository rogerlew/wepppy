"""Validate report dependencies and PDF text; emit a figure identity manifest."""
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader


def main():
    here = Path(__file__).resolve().parent
    report = here.parent.parent
    repo = report.parents[2]
    main_tex = report / "topanga-small-mutation-census-report.tex"
    source = main_tex.read_text()
    supplement = (report / "remediation-assessment.tex").read_text()
    combined = source.replace(r"\input{remediation-assessment.tex}", supplement)
    files = []
    for name in re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", combined):
        candidate = report / name
        if not candidate.exists():
            candidate = (repo / "docs/work-packages/20260809_peakflow_topanga_census_execution/artifacts" / name)
        assert candidate.is_file(), name
        files.append(candidate.resolve())
    expected_first = [f"figure-{i}.png" for i in range(1, 4)]
    assert [p.name for p in files[:3]] == expected_first
    assert len(files) == 13, len(files)
    files += [here / name for name in (
        "plot_totalwatsed.py", "selection.json", "totalwatsed-comparison.json")]
    manifest = [{"path": str(p.relative_to(repo)), "bytes": p.stat().st_size,
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    (here / "figure-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for md in (report / "README.md", here / "README.md"):
        for target in re.findall(r"\]\(([^)]+)\)", md.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (md.parent / target.split("#")[0]).exists(), target
    reader = PdfReader(report / "topanga-small-mutation-census-report.pdf")
    text = "\n".join(page.extract_text() for page in reader.pages)
    text = re.sub(r"(?<=\d)\s+\.(?=\d)", ".", text)
    for phrase in ("18.30%", "0.108%", "967.20", "1.3212%", "2,356", "0.305",
                   "Current Remediation Conclusion", "Original August Topanga Results"):
        assert phrase in text, phrase
    assert "??" not in text
    captions = re.findall(r"Figure (\d+):", text)
    assert captions == [str(i) for i in range(1, 14)], captions
    result = {"pages": len(reader.pages), "figures": len(captions),
              "dependencies_and_links": "pass", "pdf_text": "pass",
              "pdf_sha256": hashlib.sha256(
                  (report / "topanga-small-mutation-census-report.pdf").read_bytes()).hexdigest()}
    (here / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

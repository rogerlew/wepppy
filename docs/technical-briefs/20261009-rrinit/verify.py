"""Check revision 1 against committed evidence; record the owner's approval."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
STUDY = REPO / 'docs/work-packages/20261009_rrinit_parameter_review'
CHANGE = 'bae734d71165e58d610d5282d41684113b18b4ff'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pdf = HERE / 'build/main.pdf'
    log = (HERE / 'build/main.log').read_text()
    assert not re.search(r'Overfull|Underfull|undefined|Warning', log)
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    for token in ('PUBLICATION APPROVED', 'Roger Lew', 'University of Idaho',
                  'rogerlew@uidaho.edu', 'AI authoring disclosure', '17.49%',
                  '107,491.6793', '107,491.6443', '819.45', '676.12', '3,465'):
        assert token in text, token
    for token in ('/home/', '/workdir/', '/wc1/', 'YYYY', '??',
                  'REVIEW DRAFT', 'PUBLICATION APPROVAL PENDING'):
        assert token not in text, token
    assert '0 embedded files' in subprocess.check_output(
        ['pdfdetach', '-list', str(pdf)], text=True)
    info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
    assert re.search(r'JavaScript:\s+no', info)
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    bounds = subprocess.check_output(['pdftotext', '-bbox', str(pdf), '-'])
    root = ET.fromstring(bounds)
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    for page in root.findall('.//x:page', ns):
        width, height = float(page.attrib['width']), float(page.attrib['height'])
        for word in page.findall('.//x:word', ns):
            b = {k: float(v) for k, v in word.attrib.items()}
            assert 0 <= b['xMin'] <= b['xMax'] <= width, word.text
            assert 0 <= b['yMin'] <= b['yMax'] <= height, word.text
    comparison = STUDY / 'artifacts/low-forest-4v6/comparisons.csv'
    with comparison.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 16
    sandy = [r for r in rows if r['texture'] == 'sand loam']
    assert len(sandy) == 4
    for row in sandy:
        assert round(float(row['pass_sediment_kg_baseline']), 2) == 819.45
        assert round(float(row['pass_sediment_kg_trial']), 2) == 676.12
        assert round(float(row['pass_sediment_kg_pct']), 2) == -17.49
        assert round(float(row['pass_surface_m3_delta']), 3) == -0.035
        assert int(row['pass_peakro_changed_dates']) == 28
        assert int(row['pass_sediment_kg_changed_dates']) == 30
    for row in rows:
        assert int(row['pass_trial_only_dates']) == 0
        assert int(row['pass_baseline_only_dates']) == 0
        if row not in sandy:
            for field in ('runoff_mm_delta', 'pass_sediment_kg_delta', 'peak_max_m3_s_delta'):
                assert float(row[field]) == 0
    evidence = [comparison, STUDY / 'artifacts/low-forest-4v6/identity.json',
                STUDY / 'low-forest-4v6-results.md', STUDY / 'sensitivity-results.md',
                STUDY / 'assessment.md',
                REPO / 'docs/adrs/ADR-0083-low-severity-forest-initial-random-roughness.md']
    identity = json.loads(evidence[1].read_text())
    assert identity['binary_sha256'] in text
    assert CHANGE in text
    manifest = dict(schema='wepppy-technical-brief-v1', brief_id='TB-20261009-RRINIT',
        title='Low-Severity Forest Initial Random Roughness', author='Roger Lew',
        affiliation='University of Idaho', contact='rogerlew@uidaho.edu',
        document_revision='1', document_date='2026-10-10', change_date='2026-10-09',
        change_commit=CHANGE, publication_status='approved', approved_by='Roger Lew',
        approved_on='2026-10-10',
        approval_record='Roger Lew: i approve the technical brief for publication',
        previous_document_revision='0.1 (unpublished review draft)',
        pdf_filename='20261009-rrinit-r1.pdf', pdf_sha256=sha(pdf), pages=pages,
        public_path='/weppcloud/static/reports/wepppy/technical-briefs/20261009-rrinit/20261009-rrinit-r1.pdf',
        study_binary='wepp_261009_hill', study_binary_sha256=identity['binary_sha256'],
        evidence=[dict(path=str(p.relative_to(REPO)), sha256=sha(p)) for p in evidence])
    target = HERE / 'publication-manifest.json'
    if target.exists():
        assert json.loads(target.read_text())['publication_status'] in ('review_draft', 'approved')
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    checks = dict(pages=pages, pdf_sha256=sha(pdf), comparison_rows=16,
                  status='author checks passed; Roger Lew approved publication; no independent peer-review certification',
                  source_hashes={p.name: sha(p) for p in sorted(HERE.glob('*.tex'))})
    (HERE / 'document-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()

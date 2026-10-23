"""Bounded reviewed prose refresh; reject any changed model, analyzer or numeric evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from tests.roads.extract_fixture import digest
from tests.roads.roads_analysis import SUITE, source_hashes
from tests.roads.roads_report import render

provenance_path = SUITE / 'analysis_provenance_current.json'
provenance = json.loads(provenance_path.read_text())
current = source_hashes()
previous = provenance['source_sha256']
assert current.keys() == previous.keys()
changed = [name for name in current if current[name] != previous[name]]
assert changed == ['tests/roads/analysis_context.md'], changed
result_path = SUITE / 'matrix_results_current.json'
assert digest(result_path) == provenance['results_sha256']
report_path = SUITE / 'analysis_results_current.md'
assert digest(report_path) == provenance['report_sha256']
payload = json.loads(result_path.read_text())
provenance['interpretation_revision'] = {
    'previous_report_sha256': provenance['report_sha256'],
    'previous_context_sha256': previous[changed[0]],
    'native_analysis_utc': provenance['generated_utc'],
    'review': 'Independent accounting reviewer: qualify near-zero denominator in no-traffic/low-traffic contrast; all native metrics independently reconciled.',
}
provenance['source_sha256'] = current
provenance['generated_utc'] = datetime.now(timezone.utc).isoformat()
text = render(payload['cases'], payload['projects'], provenance)
provenance['report_sha256'] = hashlib.sha256(text.encode()).hexdigest()
encoded = json.dumps(provenance, indent=2, allow_nan=False) + '\n'
report_path.write_text(text)
provenance_path.write_text(encoded)
print('Reviewed interpretation refreshed; numeric evidence unchanged')

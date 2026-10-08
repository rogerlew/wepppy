"""Confirm a real mixed land/masked batch fails without publishing entries."""
import json
import os
from pathlib import Path

from wepppy.climates.prism.bulk_client import PrismBulkClient, PrismCoverageError

here=Path(__file__).resolve().parent
client=PrismBulkClient()
entries=client.cache.root/'entries/2020-01-01_2020-01-03'
before={p.name:p.read_bytes() for p in entries.glob('*.json')}
attempts=set((client.cache.root/'attempts').iterdir())
try:
    client.retrieve({'palouse':(-116.5,46.5),'pacific':(-124.9,40.0)},'2020-01-01','2020-01-03')
except PrismCoverageError as error:
    detail=str(error)
else:
    raise AssertionError('Expected explicit masked-cell failure')
assert before=={p.name:p.read_bytes() for p in entries.glob('*.json')}
created=set((client.cache.root/'attempts').iterdir())-attempts
assert len(created)==1
attempt=created.pop()
assert (attempt/'bulk.csv.gz').exists()
assert json.loads((attempt/'status.json').read_text())['state']=='failed'
record=dict(uid=os.getuid(),gid=os.getgid(),error=detail,failed_attempt=str(attempt),raw_payload_retained=True,no_entries_published=True)
(here/'live-coverage-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(record)

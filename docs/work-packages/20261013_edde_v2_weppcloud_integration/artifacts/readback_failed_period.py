"""Read downstream calendar metadata after a valid replacement fails."""
import json,hashlib
from pathlib import Path
from wepppy.nodb.core import Climate
HERE=Path(__file__).resolve().parent
root=Path('/wc1/runs/ed/edde-ca-prism-rejected-20261014')
c=Climate.getInstance(str(root))
prior=json.loads((HERE/'period-rejection-submission.json').read_text())['prior_cli_hashes']
current={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'climate').glob('*.cli')}
assert current==prior
assert (c.future_start_year,c.future_end_year)==(2061,2062)
assert c.input_years==1 and c.calendar_start_year==2060
record={'requested_years':[c.future_start_year,c.future_end_year], 'wepp_input_years':c.input_years,
        'wepp_calendar_start_year':c.calendar_start_year,'published_years':[c.edde_provenance['start_year'],c.edde_provenance['end_year']],
        'published_cli_hashes':current,'prior_publication_unchanged':True}
(HERE/'failed-period-readback.json').write_text(json.dumps(record,indent=2)+'\n')
print(record)

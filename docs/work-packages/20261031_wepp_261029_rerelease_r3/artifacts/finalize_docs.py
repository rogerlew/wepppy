"""Close release tracking after complete counted application coverage."""
from pathlib import Path
import json
R=Path('/workdir/wepppy');P=R/'docs/work-packages/20261031_wepp_261029_rerelease_r3'
x=json.loads((P/'artifacts/application-disposition.json').read_text())['completed_segmented_coverage'];assert x['failed']==x['errors']==0
counts=f"{x['passed']:,} passed / {x['skipped']:,} skipped"
p=P/'tracker.md';s=p.read_text().replace('- Pending: final full-application shard and final evidence/delivery commit.',f'- Complete isolated application coverage: {counts}, counted once across\n  successful shards and the unchanged full-shard replay. Failed attempts retained.\n- Native delivery pushed as `eb601ce8d`; final WEPPpy evidence/delivery commit follows.');p.write_text(s)
p=P/'prompts/active/rerelease_execplan.md';s=p.read_text().replace('- [ ] Complete isolated application regression coverage (shards1/4 and full\n  shard3 replay pass; slow soil-generation shard2 remains).',f'- [x] Complete isolated application regression coverage: {counts};\n  failed initial attempts retained and excluded, successful coverage counted once.').replace('- [ ] Retain evidence, update ADR/contracts/user documentation and both trackers.','- [x] Retain native evidence, update accepted ADR/contracts/user documentation and\n  both trackers. Final delivery archive/commit records finish the handoff.')
a=s.index('## Outcomes & Retrospective');b=s.index('## Context and execution',a)
s=s[:a]+f'''## Outcomes & Retrospective

Artifact revision 3 replaces the undeployed same-name matched pair. Final native
and scientific gates pass; actual vendored provenance, four smokes, 142 targeted
tests and fresh hillslope/watershed readers pass. Isolated application coverage:
{counts}. The reviewed 20-page/eight-figure report and manifest are
published and actual local HTTP hashes/MIME/navigation verified. Older reports
remain unchanged. Native delivery is pushed (`eb601ce8d`); WEPPpy delivery is
scoped to this release and its retained Roads evidence.

Roads magnitude remains unmet (744/840 versus 749/840 previously); no parameter
candidate is adopted. No production deployment, default switch or UI implementation.
Toolchain PATH must pin binutils as well as compiler; final dated outputs were
rerun rather than inferred from research-binary parity. Complete-pair staging
must precede consumers, and Unix-socket tests require short temporary paths.

'''+s[b:];p.write_text(s)
p=P/'package.md';s=p.read_text().replace('Status: active.','Status: complete locally; release delivery committed separately from deployment.');s+=f'\nFinal application coverage: **{counts}**, completed in retained segments;\n142 targeted tests and fresh selected-run/readback checks pass. The reviewed\nrevision-3 PDF/manifest are published locally and HTTP-verified. See tracker and\n`artifacts/application-disposition.json` for failed-attempt accounting.\n';p.write_text(s)
p=R/'PROJECT_TRACKER.md';s=p.read_text();a=s.index('Active: [WEPP 261029 artifact revision 3]');b=s.index('\n',a);s=s[:a]+f'Completed locally: [WEPP 261029 artifact revision 3](docs/work-packages/20261031_wepp_261029_rerelease_r3/package.md) — matched pair and reviewed illustrated report reissued; 1,095 native tests, 28 watchlist, 99 Disturbed, 840 Roads physical and fresh Cedar audits pass. Isolated application coverage: {counts}; failed attempts retained. No deployment/default change.'+s[b:];p.write_text(s)
p=P/'artifacts/integration-gates.json';j=json.loads(p.read_text());j['gates']['application_suite']='pass; complete segmented isolated coverage; see application-disposition.json';j['application_counts']=x;p.write_text(json.dumps(j,indent=2)+'\n')
print(counts)

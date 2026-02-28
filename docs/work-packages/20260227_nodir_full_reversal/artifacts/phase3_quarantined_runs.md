# Phase 3 Quarantined Runs

- Generated: 2026-02-27 07:09Z
- Source audit: `phase3_bulk_apply_audit.jsonl`
- Total quarantined run/root pairs: 3880
- Unique runs quarantined: 970

## Status Breakdown

- `readonly_required`: 3880

## Quarantine Disposition

- Disposition: `open_for_retry_after_readonly_prep`
- Required precondition before re-run: create `WD/READONLY` for targeted runs (maintenance mode), then rerun restore apply with resume.
- Canonical run/root/status ledger remains the JSONL audit file; this document provides operational summary and retry policy.

## Representative Failed Pairs (first 40)

| runid | root | status |
| --- | --- | --- |
| aberrant-grassland | climate | readonly_required |
| aberrant-grassland | landuse | readonly_required |
| aberrant-grassland | soils | readonly_required |
| aberrant-grassland | watershed | readonly_required |
| abysmal-inquisition | climate | readonly_required |
| abysmal-inquisition | landuse | readonly_required |
| abysmal-inquisition | soils | readonly_required |
| abysmal-inquisition | watershed | readonly_required |
| accelerative-tribute | climate | readonly_required |
| accelerative-tribute | landuse | readonly_required |
| accelerative-tribute | soils | readonly_required |
| accelerative-tribute | watershed | readonly_required |
| accepted-maggot | climate | readonly_required |
| accepted-maggot | landuse | readonly_required |
| accepted-maggot | soils | readonly_required |
| accepted-maggot | watershed | readonly_required |
| accursed-attitude | climate | readonly_required |
| accursed-attitude | landuse | readonly_required |
| accursed-attitude | soils | readonly_required |
| accursed-attitude | watershed | readonly_required |
| accustomed-pewter | climate | readonly_required |
| accustomed-pewter | landuse | readonly_required |
| accustomed-pewter | soils | readonly_required |
| accustomed-pewter | watershed | readonly_required |
| ace-sit-in | climate | readonly_required |
| ace-sit-in | landuse | readonly_required |
| ace-sit-in | soils | readonly_required |
| ace-sit-in | watershed | readonly_required |
| acid-fast-botulism | climate | readonly_required |
| acid-fast-botulism | landuse | readonly_required |
| acid-fast-botulism | soils | readonly_required |
| acid-fast-botulism | watershed | readonly_required |
| actinic-mariachi | climate | readonly_required |
| actinic-mariachi | landuse | readonly_required |
| actinic-mariachi | soils | readonly_required |
| actinic-mariachi | watershed | readonly_required |
| actuarial-wakefulness | climate | readonly_required |
| actuarial-wakefulness | landuse | readonly_required |
| actuarial-wakefulness | soils | readonly_required |
| actuarial-wakefulness | watershed | readonly_required |

## Retrieval Command

```bash
python3 - <<'PY'
import json
from pathlib import Path
path = Path('docs/work-packages/20260227_nodir_full_reversal/artifacts/phase3_bulk_apply_audit.jsonl')
for line in path.read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    if rec.get('status') in {'active_run_locked','root_lock_failed','readonly_required','nodir_error','exception'}:
        print(f"{rec['runid']},{rec['root']},{rec['status']}")
PY
```

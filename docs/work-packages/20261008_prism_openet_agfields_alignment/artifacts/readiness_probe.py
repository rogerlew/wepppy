"""Exercise actual readiness/annual schedule validation on isolated forest inputs."""
from pathlib import Path
from unittest.mock import patch
import json
import pandas as pd
from wepppy.nodb.core import Climate
from wepppy.nodb.mods.ag_fields import AgFields

out=Path(__file__).resolve().parent
climate=Climate.getInstance('/wc1/runs/ch/chemotherapeutic-scope')
results=[]
for spatial in [1,2]:
    for hill in [38,42,86]:
        wd=Path(f'/wc1/prism-downstream-alignment-20261008/mode{spatial}-hill{hill}')
        ctl=AgFields(str(wd),'disturbed9002_wbt.cfg')
        Path(ctl.subfields_parquet_path).unlink(missing_ok=True)
        with patch.object(Climate,'getInstance',return_value=climate):
            before=ctl.get_readiness()
            assert before['observed_climate'] is True
            assert before['parent_wepp'] is False
            path=Path(ctl.subfields_parquet_path)
            path.parent.mkdir(parents=True,exist_ok=True)
            pd.DataFrame([{'wepp_id':hill}]).to_parquet(path)
            with ctl.locked():
                ctl._field_columns=['field_id','Crop2019','Crop2020','Crop2021']
            ctl.validate_rotation_accessor('Crop{}')
            with ctl.locked():
                ctl._field_columns=['field_id','Crop2019','Crop2021']
            try:
                ctl.validate_rotation_accessor('Crop{}')
            except ValueError as exc:
                assert 'Crop2020' in str(exc)
            else:
                raise AssertionError('Missing crop year accepted')
            after=ctl.get_readiness()
            assert after['observed_climate'] and after['parent_wepp']
            assert after['observed_start_year']==2019 and after['observed_end_year']==2021
            assert after['watershed_abstraction'] is False
            results.append({'spatial':spatial,'wepp_id':hill,'before':before,'after':after,
                            'full_crop_schedule':'accepted','missing_2020':'rejected'})
(out/'readiness.json').write_text(json.dumps(results,indent=2)+'\n')
print({'readiness_cases':len(results),'calendar_schedule_validation':'passed'})

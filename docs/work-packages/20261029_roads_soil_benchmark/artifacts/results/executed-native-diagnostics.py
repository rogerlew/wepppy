"""Retain native modern PASS diagnostics separately from cross-version metrics."""
from pathlib import Path
import json
import pyarrow.parquet as pq
from wepppyo3 import wepp_interchange
from wepppy.wepp.interchange.versioning import INTERCHANGE_VERSION
import benchmark as b


def main():
    root=b.DEFAULT_ROOT
    destination=root/'native-diagnostics-v2'
    destination.mkdir(exist_ok=False)
    cases=['birmingham-loam-outrut-gravel-low','birmingham-loam-outrut-paved-high',
           'denver-loam-outrut-gravel-low']
    records=[]
    for stem in cases:
        for variant in ('legacy','generated','road_combined','all_combined','cloud_legacy'):
            name=stem+'-modern-'+variant
            source=root/'validation-v4'/name/'output/H1.pass.dat'
            target=destination/(name+'.parquet')
            wepp_interchange.hillslope_pass_files_to_parquet([str(source)],str(target),
                INTERCHANGE_VERSION.major,INTERCHANGE_VERSION.minor,cli_calendar_path=None,
                pass_family='legacy_ascii',compression='snappy')
            table=pq.read_table(target).to_pylist()
            years=len({r['year'] for r in table})
            if years!=16 or len(table)!=5844:
                raise ValueError('Incomplete native diagnostic calendar')
            rowsum=lambda k:sum(r[k] for r in table)/years
            export=sum(r['runvol']*sum(r[f'sedcon_{i}'] for i in range(1,6)) for r in table)/years
            original=json.loads((source.parent.parent/'record.json').read_text())
            records.append(dict(name=name,source_sha256=b.digest(source),parquet_sha256=b.digest(target),
                rows=len(table),pass_detachment_kg_yr=rowsum('tdet'),signed_deposition_kg_yr=rowsum('tdep'),
                pass_export_kg_yr=export,surface_volume_m3_yr=rowsum('runvol'),
                lateral_volume_m3_yr=rowsum('sbrunv'),baseflow_volume_m3_yr=rowsum('gwbfv'),
                common_report=original['metrics']))
    b.dump(destination/'summary.json',dict(script_sha256=b.digest(__file__),
        native_sha256={p.name:b.digest(p) for p in Path(wepp_interchange.__file__).parent.glob('*.so')},records=records))
    print(f'Validated {len(records)} modern native PASS diagnostics')


if __name__=='__main__':
    main()

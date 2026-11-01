"""Read official BC field metadata and exercise the current SIFT serializer."""
import argparse
import hashlib
import json
from pathlib import Path
from osgeo import ogr
from wepppy.locales.canada.bc.soils.sift.sift import SiftHorizon
from wepppy.wepp.soils.rock_fragments import rock_volume_to_mass_fraction

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--dictionary',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path)
a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
ds=ogr.Open(str(a.dictionary),0)
if ds is None:raise ValueError('Cannot read BC metadata dictionary')
layer=ds.GetLayerByName('SOILS_Metadata_Items')
rows=[]
for feature in layer:
    if feature.GetField('FGDB_Name') in {'COFRAG','BD','KP33','KP1500'}:
        rows.append({key:feature.GetField(key) for key in ['Item_MetaData_ID','FGDB_Name','FGDB_Definition','BCSLF','Published_BCSLF']})
if len(rows)!=4:raise ValueError('Expected exactly four unique source definitions')
# This synthetic row exercises the actual adapter/serializer, not a live BC extraction.
source={'COFRAG':20.,'BD':1.3,'TCLAY':20.,'TSAND':40.,'TSILT':40.,
        'VFSAND':0.,'ORGCARB':1.,'WOOD':0.,'CEC':10.,'KSAT':10.,
        'LDEPTH':20.,'HZN_MAS':'B','SOILNAME':'synthetic-basis-observation'}
h=SiftHorizon(source)
h.anisotropy=1.;h.field_cap=.2;h.wilt_pt=.1
h.interrill=100000.;h.rill=.0001;h.shear=1.
emitted=str(h)
(a.out/'observed-horizon.txt').write_text(emitted+'\n')
expected=100*rock_volume_to_mass_fraction(source['COFRAG']/100,source['BD'])
if not h.valid or float(emitted.split()[-1])!=20.:raise AssertionError('Unexpected current SIFT boundary')
if abs(expected-33.75796178343949)>1e-12:raise AssertionError('Independent mass inventory differs')
source_path=Path(__import__('inspect').getfile(SiftHorizon))
result={'metadata':rows,'source_record':source,'actual_rfg_mass_field':float(emitted.split()[-1]),
        'density_based_mass_percent':expected,'current_emission_preserves_volume_as_mass':True,
        'sift_source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'limitations':['Synthetic serializer observation; local configured BC dataset absent.',
        'No production correction or native consumer run in this probe.',
        'Retention fields in this synthetic example are explicit harness inputs, not source-derived estimates.']}
(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

"""Direct-file Climate adapter boundary and numerical rainfall tests."""
from dataclasses import replace
import json

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.postfire_debris_flow import rainfall as r
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io

pytestmark = pytest.mark.unit


def climate(tmp_path, **columns):
    data = {'prcp':[1.,2.,0.], 'year':[1,1,2], 'month':[1,1,1],
            'day_of_month':[1,1,2], 'sim_day_index':[1,2,3],
            'peak_intensity_15':[40.,0.,20.], 'peak_intensity_30':[30.,-1.,10.],
            'peak_intensity_60':[20.,float('nan'),10.]}
    data.update(columns)
    p = tmp_path/'climate.parquet'
    pd.DataFrame(data).to_parquet(p,index=False)
    return r.RainfallInputs(tmp_path/'manifest.json',p,{str(p):io.digest(p)},
                           'controlled','cligen','simulation_labels','controlled')


def test_events_conversion_duplicates_zero_and_missing(tmp_path):
    inputs = climate(tmp_path)
    rows,_,info = r.climate_events(inputs,(15,30,60),{})
    assert len(rows) == 6
    assert [v['rainfall_mm'] for v in rows[:3]] == [10.,15.,20.]
    assert rows[3]['rainfall_mm'] == 0
    assert rows[4]['reason'] == 'negative_intensity'
    assert rows[5]['reason'] == 'missing_intensity'
    assert rows[0]['event_id'] != rows[3]['event_id']
    assert rows[0]['date_status'] == 'simulation_labels'
    assert info['wet_years'] == 1
    assert info['represented_years'] == 2


def test_missing_duration_keeps_other_durations_and_original_ordinal(tmp_path):
    inputs=climate(tmp_path,prcp=[0.,1.,2.])
    df=pd.read_parquet(inputs.cli_parquet).drop(columns='peak_intensity_30')
    df.to_parquet(inputs.cli_parquet,index=False)
    inputs=replace(inputs,expected_sha256={str(inputs.cli_parquet):io.digest(inputs.cli_parquet)})
    rows,_,_=r.climate_events(inputs,(15,30,60),{})
    assert rows[0]['row_ordinal']==1
    assert rows[1]['reason']=='missing_duration'
    assert rows[3]['rainfall_mm']==5


@pytest.mark.parametrize('prcp', [[0.,0.,0.], []])
def test_dry_empty(tmp_path,prcp):
    p=tmp_path/'empty.parquet'
    pd.DataFrame({'prcp':pd.Series(prcp,dtype=float),'year':pd.Series([1]*len(prcp),dtype=float)}).to_parquet(p,index=False)
    inputs=r.RainfallInputs(p,p,{str(p):io.digest(p)},'controlled','cligen','simulation_labels','controlled')
    rows,_,info=r.climate_events(inputs,(15,30,60),{})
    assert rows==[] and info['wet_years']==0


@pytest.mark.parametrize('column,value', [('prcp',-1),('prcp',float('inf')),('prcp',float('nan'))])
def test_invalid_precipitation(tmp_path,column,value):
    inputs=climate(tmp_path,**{column:[value,1.,1.]})
    with pytest.raises(io.RainfallError,match='Precipitation'):
        r.climate_events(inputs,(15,),{})


def test_invalid_date_does_not_drop_storm(tmp_path):
    inputs=climate(tmp_path,month=[13,1,1],year=[float('nan'),1.,2.])
    rows,_,info=r.climate_events(inputs,(15,),{})
    assert len(rows)==2 and rows[0]['date_status']=='invalid_or_missing'
    assert info['invalid_wet_year_labels']


def test_hash_symlink_and_non_numeric_parquet(tmp_path):
    inputs=climate(tmp_path)
    with pytest.raises(io.RainfallError) as e:
        r.climate_events(replace(inputs,expected_sha256={str(inputs.cli_parquet):'0'*64}),(15,),{})
    assert e.value.code=='provenance_mismatch'
    link=tmp_path/'link';link.symlink_to(inputs.cli_parquet)
    with pytest.raises(io.RainfallError,match='Symlinks'):
        io.regular(link)
    p=tmp_path/'nested.parquet';pq.write_table(pa.table({'prcp':[[1.,2.]],'year':[1]}),p)
    with pytest.raises(io.RainfallError,match='primitive'):
        io.read_table(p,max_rows=10,numeric=True)
    with pytest.raises(io.RainfallError) as e:
        io.read_table(inputs.cli_parquet,max_rows=1,numeric=True)
    assert e.value.code=='resource_limit'


def test_json_duplicate_and_nonfinite(tmp_path):
    p=tmp_path/'data.json'
    for data in ('{"a":1,"a":2}','{"a":NaN}','{"a":1e400}','[]'):
        p.write_text(data)
        with pytest.raises(io.RainfallError):io.read_json(p)


def noaa_file(tmp_path,text=None):
    p=tmp_path/'noaa.csv'
    p.write_text(text or '\n'.join(['Point precipitation frequency estimates (millimeters/hour)',
        'NOAA Atlas 14 Volume 1 Version 5','Data type: Precipitation intensity',
        'Time series type: Partial duration','Latitude: 33 Degree','Longitude: -109 Degree',
        '','PRECIPITATION FREQUENCY ESTIMATES','by duration for ARI (years):, 1,2,5,10',
        '15-min:, 40,50,60,70','30-min:, 20,30,40,50','60-min:, 0,10,20,30','','Date/time (GMT): controlled']))
    return p


def test_noaa_source_and_placeholder(tmp_path):
    p=noaa_file(tmp_path)
    parsed=r.frequency_csv(p,{str(p):io.digest(p)},{},source='noaa')
    rows=r.noaa_design(parsed,(1,2,5,10),(15,30,60))
    assert len(rows)==12 and rows[0]['rainfall_mm']==10
    assert rows[2]['reason']=='zero_placeholder'
    assert all(v['reason']=='missing_noaa' for v in r.noaa_design(None,(1,),(15,30,60)))


@pytest.mark.parametrize('before,after', [('millimeters/hour','millimeters'),
    ('15-min:, 40,50,60,70','15-min:, 40,50'),('15-min:, 40,50,60,70','15-min:, NaN,50,60,70'),
    ('30-min:, 20,30,40,50','15-min:, 20,30,40,50'),('1,2,5,10','1,1,5,10'),('33 Degree','999 Degree'),
    ('Data type: Precipitation intensity','Data type: Precipitation depth'),
    ('PRECIPITATION FREQUENCY ESTIMATES','UPPER CONFIDENCE LIMITS')])
def test_malformed_noaa(tmp_path,before,after):
    p=noaa_file(tmp_path);p.write_text(p.read_text().replace(before,after))
    with pytest.raises(io.RainfallError):r.frequency_csv(p,{str(p):io.digest(p)},{},source='noaa')


def test_cli_full_context_subset_and_short_record(tmp_path):
    from wepppy.all_your_base.stats import weibull_series
    p=tmp_path/'rank.parquet'
    df=pd.DataFrame({'prcp':[1.]*100,'year':list(range(1,101)),
                     'peak_intensity_15':list(range(100,0,-1))})
    df.to_parquet(p,index=False)
    inputs=r.RainfallInputs(p,p,{str(p):io.digest(p)},'controlled','cligen','simulation_labels','controlled')
    _,df,info=r.climate_events(inputs,(15,),{})
    all_rows=r.cli_design(df,(1,2,5,10),(15,),info)
    subset=r.cli_design(df,(10,),(15,),info)
    expected_rank=weibull_series([1,2,5,10,25,50,100],100,method='pds')[10.]
    assert subset[0]==all_rows[3]
    assert subset[0]['intensity_mm_per_hour']==100-expected_rank
    # Sparse positive support is unavailable, never a clamped rainfall value.
    df['peak_intensity_15']=0.;df.loc[0,'peak_intensity_15']=10.
    info['positive_samples']['15']=1
    sparse=r.cli_design(df,(1,),(15,),info)[0]
    assert sparse['reason']=='insufficient_positive_samples'
    assert sparse['rainfall_mm'] is None and sparse['probability'] is None
    df=df.iloc[:1]
    info={**info,'wet_years':1}
    row=r.cli_design(df,(10,),(15,),info)[0]
    assert row['reason']=='unsupported_record_length'


def test_cli_infinite_sample_cannot_shift_finite_ranks(tmp_path):
    inputs=climate(tmp_path,year=[1,2,3],peak_intensity_15=[float('inf'),40.,0.])
    _,df,info=r.climate_events(inputs,(15,),{})
    rows=r.cli_design(df,(1,2),(15,),info)
    assert all(row['reason']=='nonfinite_intensity' for row in rows)
    assert info['positive_samples']['15']==1


@pytest.mark.parametrize('positive_count,expected_reason', [(0,'no_positive_samples'),
    (1,'insufficient_positive_samples'),(9,'insufficient_positive_samples'),(10,None)])
def test_cli_rank_boundary_and_clamped_csv_parity(positive_count,expected_reason):
    # Ten wet years request zero-based rank 9 for the one-year scenario.
    # The independent CSV expectation is the existing export's final-observation clamp.
    values=[100.-i for i in range(positive_count)]+[0.]*(10-positive_count)
    df=pd.DataFrame({'prcp':[1.]*10,'year':list(range(1,11)),'peak_intensity_15':values,
                     'peak_intensity_30':list(range(100,90,-1))})
    info={'wet_years':10,'invalid_wet_year_labels':False,'positive_samples':{'15':positive_count,'30':10}}
    ranks={1:9,2:4,5:1,10:0}
    expected={period:(values[min(rank,positive_count-1)] if positive_count else 0.) for period,rank in ranks.items()}
    parsed={'periods':[1.,2.,5.,10.],'data':{'15-min intensity (mm/hour)':expected,
            '30-min intensity (mm/hour)':{period:100.-rank for period,rank in ranks.items()}}}
    rows=r.cli_design(df,(1,2,5,10),(15,30),info,parsed)
    first=rows[0]
    assert first['rank_index']==9 and first['positive_samples']==positive_count
    assert first['reason']==expected_reason
    assert first['rainfall_mm']==(22.75 if expected_reason is None else None)
    assert all(row['status']=='available' for row in rows if row['duration_minutes']==30)
    assert r.cli_design(df,(10,),(15,30),info,parsed)==rows[-2:]
    parsed['data']['15-min intensity (mm/hour)'][1]=999.
    with pytest.raises(io.RainfallError,match='rounded frequency differs'):
        r.cli_design(df,(1,),(15,),info,parsed)

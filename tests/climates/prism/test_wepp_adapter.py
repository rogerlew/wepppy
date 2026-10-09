"""Actual PRN serialization, vendored CLIGEN, and CLI readback for PRISM."""
from datetime import date
import gzip
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wepppy.climates.cligen import Cligen, CligenStationsManager, ClimateFile
from wepppy.climates.prism._bulk_protocol import parse_bulk, snap
from wepppy.climates.prism.wepp_adapter import build_cell, floor_dewpoint, read_cli, validate_years
from wepppy.nodb.locales.climate_catalog import available_climate_datasets, get_climate_dataset

pytestmark = pytest.mark.integration
SOURCE = Path(__file__).resolve().parents[3] / 'docs/investigations/20261008_prism_800m_bulk/evidence/sample_2020.csv.gz'


def source():
    df = pd.read_csv(SOURCE, compression='gzip', skiprows=10)
    df = df[df.Name == 'palouse'].copy()
    df.index = pd.to_datetime(df.Date)
    return df[['ppt (mm)', 'tmin (degrees C)', 'tmax (degrees C)', 'tdmean (degrees C)', 'soltotal (MJ/m^2/day)']].set_axis(['ppt','tmin','tmax','tdmean','soltotal'],axis=1)


def test_catalog_bounds_and_legacy_identity():
    p = get_climate_dataset('observed_prism_800m')
    assert p.climate_mode == 16 and p.spatial_modes == (0,1,2)
    assert get_climate_dataset('observed_daymet').climate_mode == 9
    assert p in available_climate_datasets(['us'], [])
    assert p not in available_climate_datasets(['canada'], [])
    for start,end in [(1980,1982),(2020,2019),(2020,date.today().year)]:
        with pytest.raises(ValueError): validate_years(start,end)


@pytest.mark.slow
def test_native_observed_cli_roundtrip_and_raw_dewpoint_revision(tmp_path):
    df = source()
    # Include a trace wet day below PRN resolution to assert documented zeroing.
    df.iloc[0,df.columns.get_loc('ppt')] = 0.01
    raw = df.copy(deep=True)
    wind = pd.DataFrame({'vs(m/s)':2.34,'th(DegreesClockwisefromnorth)':123.4},index=df.index)
    station = CligenStationsManager(version='2015').get_station_fromid('or354811')
    cligen = Cligen(station,wd=str(tmp_path))
    build_cell(cligen,df,wind,tmp_path,'cell',seed=84568,silent_pass_observed_quality_guard=True)
    pd.testing.assert_frame_equal(raw,df)
    cli = read_cli(tmp_path/'cell.cli')
    assert len(cli)==366 and cli.iloc[0].prcp==0
    assert (cli.tdew >= cli.tmin).all()
    assert np.allclose(cli.rad,df.soltotal*1e6/41840,atol=.501)
    build_cell(cligen,df,wind,tmp_path,'alias',seed=84568,silent_pass_observed_quality_guard=True)
    pd.testing.assert_frame_equal(cli,read_cli(tmp_path/'alias.cli'))
    # Exercise cooler and warmer revised Tmin with the actual CLI writer.
    for delta in [-8,8]:
        c = ClimateFile(str(tmp_path/'cell.cli'))
        c.replace_var('tmin',df.index,cli.tmin+delta)
        c.replace_var('tmax',df.index,cli.tmax+delta)
        c.write(str(tmp_path/'revised.cli'))
        floor_dewpoint(tmp_path/'revised.cli',df.tdmean,tmp_path/'revision.csv')
        actual=read_cli(tmp_path/'revised.cli')
        assert np.allclose(actual.tdew,np.maximum(df.tdmean,actual.tmin),atol=.051)

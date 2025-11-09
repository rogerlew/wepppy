"""Thin client for the hosted CLIGEN web services."""

from __future__ import annotations

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import join as _join

import json
from typing import Any

import requests
from posixpath import join as urljoin
import time

from wepppy.all_your_base import isint, isfloat

_cligen_url = "https://wepp.cloud/webservices/cligen/"


def fetch_multiple_year(
    par: int,
    years: int,
    lng: float | None = None,
    lat: float | None = None,
    p_mean: str | None = None,
    p_std: str | None = None,
    p_skew: str | None = None,
    p_wd: str | None = None,
    p_ww: str | None = None,
    tmax: str | None = None,
    tmin: str | None = None,
    dewpoint: str | None = None,
    solrad: str | None = None,
    returnjson: bool = True,
    randseed: int | None = None,
    version: str = '2015',
) -> dict[str, Any] | str:
    """Request a multi-year CLIGEN run from the hosted service.

    See https://wepp.cloud/webservices/cligen/multiple_year/<par>/ for parameter
    semantics.

    Args:
        par: Station identifier.
        years: Number of years to simulate remotely.
        lng: Optional longitude override.
        lat: Optional latitude override.
        p_mean: Monthly precip source (`prism` or `daymet`).
        p_std: Precip standard deviation source (`daymet`).
        p_skew: Precip skew source (`daymet`).
        p_wd: Wet→dry probability source (`daymet`).
        p_ww: Wet→wet probability source (`daymet`).
        tmax: Maximum temperature source (`prism`).
        tmin: Minimum temperature source (`prism`).
        dewpoint: Dew point source (`daymet`).
        solrad: Solar radiation source (`daymet`).
        returnjson: When True, decode the JSON payload; otherwise return text.
        randseed: Optional CLIGEN random seed.
        version: Station catalog version (`2015` or other server-supported tag).

    Returns:
        Parsed JSON dictionary or the raw `.cli` text depending on
        ``returnjson``.
    """

    url = urljoin(_cligen_url, 'multiple_year', str(par))

    assert isint(years)

    data = {'years': int(years),
            'version': version}

    if lng is not None:
        lng = float(lng)
        data['lng'] = lng

    if lat is not None:
        lat = float(lat)
        data['lat'] = lat

    if p_mean is not None:
        p_mean = p_mean.lower()
        assert p_mean in ['prism', 'daymet']
        data['p_mean'] = p_mean

    if p_std is not None:
        p_std = p_std.lower()
        assert p_std in ['daymet']
        data['p_std'] = p_std

    if p_skew is not None:
        p_skew = p_skew.lower()
        assert p_skew in ['daymet']
        data['p_skew'] = p_skew

    if p_ww is not None:
        p_ww = p_ww.lower()
        assert p_ww in ['daymet']
        data['p_ww'] = p_ww

    if p_wd is not None:
        p_wd = p_wd.lower()
        assert p_wd in ['daymet']
        data['p_wd'] = p_wd

    if tmax is not None:
        tmax = tmax.lower()
        assert tmax in ['prism']
        data['tmax'] = tmax

    if tmin is not None:
        tmin = tmin.lower()
        assert tmin in ['prism']
        data['tmin'] = tmin

    if dewpoint is not None:
        dewpoint = dewpoint.lower()
        assert dewpoint in ['daymet']
        data['dewpoint'] = dewpoint

    if solrad is not None:
        solrad = solrad.lower()
        assert solrad in ['daymet']
        data['solrad'] = solrad

    if randseed is not None:
        assert int(randseed) >= 0
        data['randseed'] = randseed
        
    assert returnjson is True or returnjson is False or \
        returnjson == 1 or returnjson == 0

    data['returnjson'] = returnjson
    data['version'] = version

    r = requests.post(url, json=data)

    if r.status_code != 200:
        raise Exception('Encountered error retrieving from cligen: {}'.format(r.text))

    if returnjson:
        return json.loads(r.text)

    return r.text


def selected_single_storm(
    par: int,
    storm_date: str,
    design_storm_amount_inches: float,
    duration_of_storm_in_hours: float,
    time_to_peak_intensity_pct: float,
    max_intensity_inches_per_hour: float,
    cliver: float = 5.3,
    returnjson: bool = True,
    version: str = '2015',
) -> dict[str, Any] | str:
    """Request a single-storm design event from the hosted CLIGEN service.

    Args:
        par: Station identifier.
        storm_date: Date string (MM-DD-YYYY or similar) describing the event.
        design_storm_amount_inches: Total storm depth.
        duration_of_storm_in_hours: Duration of the storm event.
        time_to_peak_intensity_pct: Percent of duration until peak intensity.
        max_intensity_inches_per_hour: Desired peak intensity.
        cliver: CLIGEN binary version (5.2 or 5.3).
        returnjson: When True, decode the JSON payload; otherwise return text.
        version: Station catalog version.

    Returns:
        Parsed JSON dictionary or the raw `.cli` text depending on
        ``returnjson``.
    """

    url = urljoin(_cligen_url, 'selected_single_storm', str(par))

    if '-' in storm_date:
        storm_date = storm_date.split('-')
    elif '/' in storm_date:
        storm_date = storm_date.split('/')
    elif '.' in storm_date:
        storm_date = storm_date.split('.')
    else:
        storm_date = storm_date.split(' ')

    assert len(storm_date) == 3
    storm_date = [int(v) for v in storm_date]
    mo, da, yr = storm_date
    assert mo >= 1
    assert mo <= 12
    assert da >= 1
    assert da <= [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo-1]

    assert isfloat(design_storm_amount_inches)
    assert isfloat(duration_of_storm_in_hours)
    assert isfloat(time_to_peak_intensity_pct)
    assert isfloat(max_intensity_inches_per_hour)

    assert cliver in [5.2, 5.3]

    assert returnjson is True or returnjson is False or \
        returnjson == 1 or returnjson == 0

    data = dict(storm_date='{}-{}-{}'.format(mo, da, yr),
                design_storm_amount_inches=design_storm_amount_inches,
                duration_of_storm_in_hours=duration_of_storm_in_hours,
                time_to_peak_intensity_pct=time_to_peak_intensity_pct,
                max_intensity_inches_per_hour=max_intensity_inches_per_hour,
                cliver=cliver, returnjson=returnjson, version=version)

    r = requests.post(url, json=data)

    if r.status_code != 200:
        raise Exception('Encountered error retrieving from cligen')

    if returnjson:
        return json.loads(r.text)

    return r.text


def observed_daymet(
    par: int,
    start_year: int,
    end_year: int,
    lng: float | None = None,
    lat: float | None = None,
    returnjson: bool = True,
    version: str = '2015',
) -> dict[str, Any] | str:
    """Fetch observed Daymet data for a station from the CLIGEN web service.

    Args:
        par: Station identifier.
        start_year: First Daymet year (>= 1980).
        end_year: Final Daymet year (<= last available).
        lng: Optional longitude override used by the service.
        lat: Optional latitude override used by the service.
        returnjson: When True, decode the JSON payload; otherwise return text.
        version: Station catalog version.

    Returns:
        Parsed JSON dictionary or the raw `.cli` text depending on
        ``returnjson``.
    """
    url = urljoin(_cligen_url, "observed_daymet", str(par))

    assert isint(start_year)
    assert isint(end_year)

    start_year = int(start_year)
    end_year = int(end_year)

    d0 = 1980
    dend = int(time.strftime("%Y"))-1

    assert start_year >= d0
    assert start_year <= dend

    assert end_year >= d0
    assert end_year <= dend

    assert returnjson is True or returnjson is False or \
        returnjson == 1 or returnjson == 0

    data = dict(start_year=start_year, end_year=end_year,
                lng=lng, lat=lat, returnjson=returnjson,
                version=version)

    r = requests.post(url, json=data)

    if r.status_code != 200:
        raise Exception("Encountered error retrieving from cligen")

    if returnjson:
        return json.loads(r.text)

    return r.text


def future_rcp85(par, start_year, end_year, lng=None, lat=None, returnjson=True, version='2015'):
    url = urljoin(_cligen_url, "future_rcp85", str(par))

    assert isint(start_year)
    assert isint(end_year)

    start_year = int(start_year)
    end_year = int(end_year)

    d0 = 2006
    dend = 2099

    assert start_year >= d0
    assert start_year <= dend

    assert end_year >= d0
    assert end_year <= dend

    assert returnjson is True or returnjson is False or \
        returnjson == 1 or returnjson == 0

    data = dict(start_year=start_year, end_year=end_year,
                lng=lng, lat=lat, returnjson=returnjson,
                version=version)

    r = requests.post(url, json=data)

    if r.status_code != 200:
        raise Exception("Encountered error retrieving from %s" % url)

    if returnjson:
        return json.loads(r.text)

    return r.text


def unpack_json_result(result, fn_prefix=None, dst_dir="./"):
    """
    Utility function to save the par and climate files
    returned from the cligen webservice to disk.
    
    fn_prefix specifies the name of the files. e.g. {fn_prefix}.par,
    if fn_prefix is None then the names returned from the webservice are used
    
    dst_dir specifies the directory to save the result, defaults to working
    directory
    """
    
    if fn_prefix is not None:
        cli_fn = "{}.cli".format(fn_prefix)
        par_fn = "{}.par".format(fn_prefix)
    else:
        cli_fn = "wepp.cli"
        par_fn = "wepp.par"
        
    cli_path = _join(dst_dir, cli_fn)

    with open(cli_path, "w") as fp:
        fp.write(result["cli_contents"])

    par_path = _join(dst_dir, par_fn)

    with open(par_path, "w") as fp:
        fp.write(result["par_contents"])

    return par_fn, cli_fn, result.get("monthlies", None)


if __name__ == "__main__":
    #    from pprint import pprint

    #    r =  fetch_multiple_year(106152, 3, lng=-115, lat=46, returnjson=1)
    #    print r.keys()

    #    print selected_single_storm(106152, "4-15-17", 6.3, 6, 3, .3)
    #    print observed_daymet(106152, 1985, 1988)

    print(future_rcp85(106152, 2018, 2018))

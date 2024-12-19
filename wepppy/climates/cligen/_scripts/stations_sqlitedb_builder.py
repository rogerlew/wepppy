from os.path import exists as _exists
from os.path import split as _split
from os.path import join as _join
import os
import sys
import sqlite3
import zipfile
import shutil
import glob

from wepppy.climates.cligen import Station

from pathlib import Path


def isfloat(v):
    try:
        float(v)
        return 1
    except:
        return 0


def _p(line):
    line = line.replace('TP5', '')
    line = line.replace('TP6', '')
    line = ''.join([v for v in line if v in ' -.0123456789'])
    return line.split()


def get_state(par_path):
    state = Path(par_path).stem.upper()
    state = ''.join([c for c in state if not isfloat(c)])
    return state


def readpar(par):
    with open(par) as fid:
        desc = fid.readline().strip()
        state = get_state(par)
        print(state, par)

        line1 = _p(fid.readline())
        assert len(line1) == 4
        latitude, longitude, years, type = line1

        line2 = _p(fid.readline())
        assert len(line2) == 3, str(line2)
        elevation, tp5, tp6 = line2
    
    station = Station(par)
    annual_ppt = sum(ppt*nwd for ppt, nwd in zip(station.ppts, station.nwds))

    return '"%s"' % state, '"%s"' % desc.replace('"', ''), '"%s"' % _split(par)[-1], latitude, longitude, years, type, elevation, tp5, tp6, str(annual_ppt)


def build_db(db_fn, par_dir):
    if _exists(db_fn):
        os.remove(db_fn)

    conn = sqlite3.connect(db_fn)
    c = conn.cursor()
    c.execute('''CREATE TABLE stations
                (state text, desc text, par text, latitude real, longitude real, years real, type integer, elevation real, tp5 real, tp6 real, annual_ppt real)''')


    par_files = glob.glob(_join(par_dir, "**/*.par"), recursive=True)
    par_files += glob.glob(_join(par_dir, "**/*.PAR"), recursive=True)

    par_stems = set()
    filtered_pars = []
    for par in par_files:
        if par not in par_stems:
            filtered_pars.append(par)
            par_stems = Path(par).stem

    for par in filtered_pars:
        print(par)
        line = ','.join(readpar(par))
        print(line)
        c.execute("INSERT INTO stations VALUES (%s)" % line)

    print(len(par_files))

    conn.commit()
    conn.close()
    
    os.chmod(db_fn, 0o755)

database_defs = [
    dict(
    db_fn= 'ghcn_stations.db',
    par_dir= '../GHCN_Intl_Stations/'
    ),
    dict(
    db_fn= '2015_stations.db',
    par_dir= '../2015_par_files/'
    ),
    dict(
    db_fn= 'au_stations.db',
    par_dir= '../au_par_files/'
    ),
    dict(
    db_fn= 'stations.db',
    par_dir= '../stations/'
    )
]

for db_def in database_defs:
    build_db(**db_def)
    

import os
import json
import sqlite3
from os.path import join as _join
from os.path import exists as _exists
from glob import glob
from subprocess import Popen, PIPE

import numpy as np
import io


_thisdir = os.path.dirname(__file__)
_datadir = _join(_thisdir, "data")
_statsgo = _join(_thisdir, "statsgo")


def adapt_array(arr):
    """
    https://stackoverflow.com/a/18622264
    http://stackoverflow.com/a/31312102/190597 (SoulNibbler)
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


db_fn = _join(_thisdir, '../', 'statsgo_spatial.db')

if _exists(db_fn):
    os.remove(db_fn)

# Converts np.array to TEXT when inserting
sqlite3.register_adapter(np.ndarray, adapt_array)

# Converts TEXT to np.array when selecting
sqlite3.register_converter("array", convert_array)

conn = sqlite3.connect(db_fn, detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()


def identify_bounds(coords):
    xmin = 1e38
    xmax = -1e38
    ymin = 1e38
    ymax = -1e38

    for coord in coords:
        x, y = coord

        if x < xmin:
            xmin = x
        if x > xmax:
            xmax = x
        if y < ymin:
            ymin = y
        if y > ymax:
            ymax = y

    return xmin, ymin, xmax, ymax
"""
shps = glob("*/spatial/*.shp")

print(len(shps))

for shp in shps:
    state = shp.split("/")[0].split('_')[2]
    print(state)
    dst_fn = "../../spatial/{}.json".format(state)

    cmd = ["ogr2ogr", "-f", "GeoJSON", dst_fn, shp]
    Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
"""


# states ="""\
# Alabama	AL
# Alaska	AK
# Arizona	AZ
# Arkansas	AR
# California	CA
# Colorado	CO
# Connecticut	CT
# Delaware	DE
# Florida	FL
# Georgia	GA
# Hawaii	HI
# Idaho	ID
# Illinois	IL
# Indiana	IN
# Iowa	IA
# Kansas	KS
# Kentucky	KY
# Louisiana	LA
# Maine	ME
# Maryland	MD
# Massachusetts	MA
# Michigan	MI
# Minnesota	MN
# Mississippi	MS
# Missouri	MO
# Montana	MT
# Nebraska	NE
# Nevada	NV
# New Hampshire	NH
# New Jersey	NJ
# New Mexico	NM
# New York	NY
# North Carolina	NC
# North Dakota	ND
# Ohio	OH
# Oklahoma	OK
# Oregon	OR
# Pennsylvania	PA
# Rhode Island	RI
# South Carolina	SC
# South Dakota	SD
# Tennessee	TN
# Texas	TX
# Utah	UT
# Vermont	VT
# Virginia	VA
# Washington	WA
# West Virginia	WV
# Wisconsin	WI
# Wyoming	WY
# American Samoa	AS
# District of Columbia	DC
# Federated States of Micronesia	FM
# Guam	GU
# Marshall Islands	MH
# Northern Mariana Islands	MP
# Palau	PW
# Puerto Rico	PR
# Virgin Islands	VI"""
# _states = {}
# for state in states.split('\n'):
#     state = state.split('\t')
#     _states[state[0]] = state[-1]
# states = _states
#
# with open(_join(_thisdir, '../', 'us-states.json')) as fp:
#     data = json.load(fp)


# c.execute('''CREATE TABLE state_bounds
#              (state TEXT, xmin REAL, ymin REAL, xmax REAL, ymax REAL)''')
#
#
# for feature in data['features']:
#     state = feature['properties']['name']
#     state = states[state]
#     print(state)
#
#     if feature['geometry']['type'] == 'MultiPolygon':
#         xmin = 1e38
#         xmax = -1e38
#         ymin = 1e38
#         ymax = -1e38
#
#         coordss = feature['geometry']['coordinates']
#
#         for coords in coordss:
#             _xmin, _ymin, _xmax, _ymax = identify_bounds(coords[0])
#
#             if _xmin < xmin:
#                 xmin = _xmin
#             if _xmax > xmax:
#                 xmax = _xmax
#             if _ymin < ymin:
#                 ymin = _ymin
#             if _ymax > ymax:
#                 ymax = _ymax
#
#     if feature['geometry']['type'] == 'Polygon':
#         coords = feature['geometry']['coordinates'][0]
#         xmin, ymin, xmax, ymax = identify_bounds(coords)
#
#     print('  {}: {}, {}, {}, {}, {}'.format(state, len(coords), xmin, ymin, xmax, ymax))
#
#     c.execute('INSERT INTO state_bounds VALUES (?,?,?,?,?)',
#               [state, xmin, ymin, xmax, ymax])


c.execute('''CREATE TABLE poly_bounds
             (mukey INTEGER, state TEXT, xmin REAL, ymin REAL, xmax REAL, ymax REAL)''')

c.execute('''CREATE TABLE mukey_polys
             (mukey INTEGER, state TEXT, coords ARRAY)''')

jsons = glob('../../spatial/*.json')

for js_fn in jsons:
    state = js_fn.split('/')[1].split('.')[0]
    print(state)
    with open(js_fn) as fp:
        data = json.load(fp)

    print(len(data['features']))
    for feature in data['features']:
        coords = feature['geometry']['coordinates'][0]
        xmin, ymin, xmax, ymax = identify_bounds(coords)

        mukey = feature['properties']['MUKEY']
        print('  {}: {}, {}, {}, {}, {}'.format(mukey, len(coords), xmin, ymin, xmax, ymax))

        c.execute('INSERT INTO poly_bounds VALUES (?,?,?,?,?,?)',
                  [mukey, state, xmin, ymin, xmax, ymax])

        c.execute('INSERT INTO mukey_polys VALUES (?,?,?)',
                  [mukey, state, adapt_array(coords)])

conn.commit()
c.close()

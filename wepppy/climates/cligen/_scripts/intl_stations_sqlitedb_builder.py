from os.path import exists as _exists
from os.path import split as _split
import os
import sys
import sqlite3
import zipfile
import shutil
import glob


# n = 0
# for root, dirs, files in os.walk("C:\\WEPP\\Data\\climates\\cligen"):
#    for name in files:
#        fname = _join(root, name)
##        if fname.endswith(".ZIP"):
##            zip_ref = zipfile.ZipFile(fname, 'r')
##            zip_ref.extractall(root)
##            zip_ref.close()
##            n += 1
#        if fname.endswith(".PAR"):
#            n += 1
#            print name
#            #if not _exists(name):
#            #
#            #    print(fname)
#            shutil.copyfile(fname, _join('./',name))
# print(n)


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


def readpar(par):
    fid = open(par)
    desc = fid.readline().strip()
    state = desc.split()[0]

    line1 = _p(fid.readline())
    assert len(line1) == 4
    latitude, longitude, years, type = line1

    line2 = _p(fid.readline())
    assert len(line2) == 3, str(line2)
    elevation, tp5, tp6 = line2
    fid.close()

    return '"%s"' % state, '"%s"' % desc, '"%s"' % _split(par)[
        -1], latitude, longitude, years, type, elevation, tp5, tp6


_db_fn = 'ghcn_stations.db'

if _exists(_db_fn):
    os.remove(_db_fn)

conn = sqlite3.connect(_db_fn)
c = conn.cursor()
c.execute('''CREATE TABLE stations
             (state text, desc text, par text, latitude real, longitude real, years real, type integer, elevation real, tp5 real, tp6 real)''')

pars = glob.glob("../GHCN_Intl_Stations/30-year/*.PAR")
pars.extend(glob.glob("../GHCN_Intl_Stations/30-year/*.par"))
for par in pars:
    print(par)
    line = ','.join(readpar(par))
    c.execute("INSERT INTO stations VALUES (%s)" % line)

print(len(pars))

conn.commit()
conn.close()


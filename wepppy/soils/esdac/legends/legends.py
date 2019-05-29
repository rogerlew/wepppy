from os.path import join as _join
import os
# https://esdac.jrc.ec.europa.eu/content/european-soil-database-v2-raster-library-1kmx1km
# https://esdac.jrc.ec.europa.eu/content/sgdbe-attributes
# https://esdac.jrc.ec.europa.eu/content/ptrdb-attributes
# https://esdac.jrc.ec.europa.eu/content/legend-files


from ..esdac import _attr_fmt


_thisdir = os.path.dirname(__file__)

def _load_ptrdb_legends():
    # read the file
    with open(_join(_thisdir, 'ptrdb.dat'), 'r+', encoding="utf-8") as fp:
        lines = fp.readlines()

    # determine breaks based on the horizontal rules (e.g. -------)
    breaks = []
    for i, L in enumerate(lines):
        if L.strip().startswith('-'):
            breaks.append(i)

    # iterate over the tables and parse
    d = {}
    i0 = 0
    for i, iend in enumerate(breaks):
        _lines = lines[i0:iend]

        # split the first line to get the attribute name and description
        attr, desc = _lines[0].split('=')
        attr, desc = attr.strip(), desc.strip()
        attr = _attr_fmt(attr)
        d[attr] = dict(description=desc, table={})

        # iterate over remaining lines and pull out key value pairs
        for L in _lines[1:]:
            k, v = L.split('=')
            k, v = k.strip(), v.strip()
            d[attr]['table'][k] = v

        i0 = iend + 1

    return d


def _load_sgdpe_legends():
    # read the file
    with open(_join(_thisdir, 'sgdpe.dat'), 'r+', encoding="utf-8") as fp:
        lines = fp.readlines()

    # determine breaks based on the horizontal rules (e.g. -------)
    breaks = []
    for i, L in enumerate(lines):
        if L.startswith('-') and len(L.strip()) > 70:
            breaks.append(i)

    # iterate over the tables and parse
    d = {}
    i0 = 0
    for i, iend in enumerate(breaks):

        # catch empty tables
        _lines = lines[i0:iend]
        if len(_lines) == 0:
            continue

        # the attribute name is the first line
        attr = _lines[0].strip()
        attr = _attr_fmt(attr)
        d[attr] = dict(description=None, table={})

        # the line after the attribute should be a horizontal rule
        assert _lines[1].strip().startswith('-'), (attr, _lines[1])

        # There are carriage returns for some of the values, but some of the keys
        # are ''. Here we remove the lines with carriage returns by assuming
        # that '' is only used as a key if it is the first key-value pair in the table
        # or the value is "No Information"
        # The reformatted table is stored in tbl_lines
        tbl_lines = []
        for i, L in enumerate(_lines[2:]):
            if len(L[:4].strip()) == 0 and 'no information' not in L.lower() and i > 0:
                tbl_lines[-1] = '%s %s' %(tbl_lines[-1].rstrip(),  L.lstrip())
            else:
                tbl_lines.append(L)

        # now we can iterate over the key value pairs
        for i, L in enumerate(tbl_lines):

            # key is ''
            if len(L[:4].strip()) == 0:
                k = ''
                v = L.strip()
            else:
                tokens = L.split()
                k = tokens[0]
                v = ' '.join(tokens[1:])

            d[attr]['table'][k] = v

        i0 = iend + 1
        continue

    return d


ptrdb = _load_ptrdb_legends()
sgdpe = _load_sgdpe_legends()


def get_legend(attr):
    global ptrdb, sgdpe

    _attr = _attr_fmt(attr)

    for k in ptrdb:
        if _attr == _attr_fmt(k):
            return ptrdb[k]

    for k in sgdpe:
        if _attr == _attr_fmt(k):
            return sgdpe[k]

    raise KeyError(attr)


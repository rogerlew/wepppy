from datetime import datetime

def all_hillslopes(landuse, soils):
    return list(landuse.domlc_d.keys())

def _identify_outcrop_mukeys(soils):
    outcrop_mukeys = []
    _soils = soils.subs_summary
    for top in _soils:
        desc = _soils[top]['desc'].lower()
        if 'melody-rock outcrop' in desc or 'ellispeak-rock outcrop' in desc:
            mukey = str(_soils[top]['mukey'])
            outcrop_mukeys.append(mukey)

    return outcrop_mukeys


def not_shrub_and_not_outcrop_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if str(domsoil_d[top]) not in outcrop_mukeys and domlc_d[top] != '104':
            topaz_ids.append(top)

    return topaz_ids


def shrub_and_not_outcrop_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if str(domsoil_d[top]) not in outcrop_mukeys and domlc_d[top] == '104':
            topaz_ids.append(top)

    return topaz_ids


def not_shrub_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    topaz_ids = []
    for top in domlc_d:
        if str(domlc_d[top]) != '104':
            topaz_ids.append(top)

    return topaz_ids


def shrub_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    topaz_ids = []
    for top in domlc_d:
        if domlc_d[top] == '104':
            topaz_ids.append(top)

    return topaz_ids


def outcrop_selector(landuse, soils):
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if domsoil_d[top] in outcrop_mukeys:
            topaz_ids.append(top)

    return topaz_ids


def not_outcrop_selector(landuse, soils):
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if domsoil_d[top] not in outcrop_mukeys:
            topaz_ids.append(top)

    return topaz_ids


wd = None

def log_print(msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))

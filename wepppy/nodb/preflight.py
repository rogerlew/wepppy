from wepppy.nodb import Prep


def _safe_gt(a, b):
    if a is None or b is None:
        return False

    return a > b


def preflight_check(wd):
    try:
        prep = Prep.getInstance(wd)
    except:
        return None

    sbs_required = prep.sbs_required
    has_sbs = prep.has_sbs

    d = {}

    if sbs_required:  # baer
        d['sbs_map'] = prep['landuse_map'] is not None and has_sbs  # unchecked or burned
    else:  # disturbed
        if has_sbs:
            d['sbs_map'] = True  # burned
        else:
            d['sbs_map'] = None  # unburned

    d['channels'] = prep['build_channels'] is not None
    d['outlet'] = _safe_gt(prep['set_outlet'], prep['build_channels'])
    d['subcatchments'] = _safe_gt(prep['abstract_watershed'], prep['build_channels'])

    if prep['landuse_map'] is None:
        # disturbed w/out sbs
        d['landuse'] = _safe_gt(prep['build_landuse'], prep['abstract_watershed'])
        
        # baer where sbs is required
        if sbs_required:
            d['landuse'] = False

    # disturbed or baer with sbs
    else:
        d['landuse'] = _safe_gt(prep['build_landuse'], prep['abstract_watershed']) and \
                       _safe_gt(prep['build_landuse'], prep['landuse_map'])


    if prep['landuse_map'] is None:
        # disturbed w/out sbs
        d['soils'] = _safe_gt(prep['build_soils'], prep['abstract_watershed']) and \
                     _safe_gt(prep['build_soils'], prep['build_landuse'])
        
        # baer where sbs is required
        if sbs_required:
            d['soils'] = False

    # disturbed or baer with sbs
    else:
        d['soils'] = _safe_gt(prep['build_soils'], prep['abstract_watershed']) and \
                     _safe_gt(prep['build_soils'], prep['build_landuse']) and \
                     _safe_gt(prep['build_soils'], prep['landuse_map'])

    d['climate'] = _safe_gt(prep['build_climate'], prep['abstract_watershed'])

    d['wepp'] = _safe_gt(prep['run_wepp'], prep['build_landuse']) and \
                _safe_gt(prep['run_wepp'], prep['build_soils']) and \
                _safe_gt(prep['run_wepp'], prep['build_climate'])

    d['observed'] = _safe_gt(prep['run_observed'], prep['build_landuse']) and \
                    _safe_gt(prep['run_observed'], prep['build_soils']) and \
                    _safe_gt(prep['run_observed'], prep['build_climate']) and \
                    _safe_gt(prep['run_observed'], prep['run_wepp'])

    d['watar'] = _safe_gt(prep['run_watar'], prep['build_landuse']) and \
                 _safe_gt(prep['run_watar'], prep['build_soils']) and \
                 _safe_gt(prep['run_watar'], prep['build_climate']) and \
                 _safe_gt(prep['run_watar'], prep['run_wepp'])

    return d


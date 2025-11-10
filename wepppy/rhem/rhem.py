"""Thin helpers for running the Rangeland Hydrology and Erosion Model (RHEM)."""

from __future__ import annotations

import csv
import io
import math
import os
import subprocess
from datetime import datetime
from time import time
from typing import Dict, Sequence
from os.path import exists as _exists
from os.path import join as _join

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')
_template_dir = _join(_thisdir, 'templates')
_rhem = _join(_thisdir, "bin", "rhem_v23")


SoilTextureRow = Dict[str, str]
SoilTextureTable = Dict[str, SoilTextureRow]


def _template_loader(fn: str) -> str:
    """Load a template file from the local ``templates`` directory."""

    with io.open(_join(_template_dir, fn), "r", encoding="utf-8") as fp:
        _template = fp.readlines()

        # strip comments
        _template = [L[:L.find('#')] for L in _template]
        _template = '\n'.join(_template)

    return _template


def _par_template_loader() -> str:
    """Return the parameter template used for ``*.par`` files."""

    return _template_loader("par.template")


def read_soil_texture_table() -> SoilTextureTable:
    """Load the bundled soil texture look-up table used by RHEM."""

    fn = _join(_data_dir, 'soil_texture_table.csv')
    assert _exists(fn)

    fp = open(fn)
    csv_reader = csv.DictReader(fp)
    d: SoilTextureTable = {}
    for row in csv_reader:
        d[row['class_name'].lower()] = row
    fp.close()

    return d


soil_texture_db = read_soil_texture_table()


def make_parameter_file(
    scn_name: str,
    out_dir: str,
    soil_texture: str,
    moisture_content: float,
    bunchgrass_cover: float,
    forbs_cover: float,
    shrubs_cover: float,
    sodgrass_cover: float,
    rock_cover: float,
    basal_cover: float,
    litter_cover: float,
    cryptogams_cover: float,
    slope_length: float,
    slope_steepness: float,
    sl: Sequence[float],
    sx: Sequence[float],
    width: float,
    model_version: str,
) -> str:
    """Build a ``*.par`` input file for the provided hillslope scenario.

    Args:
        scn_name: Scenario identifier used to name artifacts.
        out_dir: Directory where the ``*.par`` file will be written.
        soil_texture: Soil texture key (matches ``soil_texture_table.csv``).
        moisture_content: Antecedent moisture fraction.
        bunchgrass_cover: Bunchgrass canopy cover percentage (0-100).
        forbs_cover: Forbs canopy cover percentage (0-100).
        shrubs_cover: Shrub canopy cover percentage (0-100).
        sodgrass_cover: Sodgrass canopy cover percentage (0-100).
        rock_cover: Rock ground cover percentage (0-100).
        basal_cover: Basal ground cover percentage (0-100).
        litter_cover: Litter ground cover percentage (0-100).
        cryptogams_cover: Cryptogam ground cover percentage (0-100).
        slope_length: Hillslope length in meters.
        slope_steepness: Hillslope slope percent.
        sl: Sequence of segment lengths used by the template.
        sx: Sequence of segment slopes matching ``sl``.
        width: Average hillslope width in meters.
        model_version: Version string persisted alongside other metadata.

    Returns:
        Absolute path to the generated ``*.par`` file.
    """

    # convert to percent values
    bunchgrass_cover = bunchgrass_cover/100
    forbs_cover = forbs_cover/100
    shrubs_cover = shrubs_cover/100
    sodgrass_cover = sodgrass_cover/100

    # canopy cover for grass (this is for the new kss equations from Sam)
    grass_cover = bunchgrass_cover + forbs_cover + sodgrass_cover

    ##
    # TOTAL CANOPY COVER
    totalcover = bunchgrass_cover + forbs_cover + shrubs_cover + sodgrass_cover
    rock_cover = rock_cover/100
    basal_cover = basal_cover/100
    litter_cover = litter_cover/100
    cryptogams_cover = cryptogams_cover/100

    ##
    # TOTAL GROUND COVER
    total_ground_cover = basal_cover + litter_cover + cryptogams_cover + rock_cover

    slope_steepness = slope_steepness/100

    # get the soil information from the database
    soil = soil_texture_db[soil_texture]

    # compute ft (replaces fe and fr)
    ft = (-1 * 0.109 +
          1.425 * litter_cover +
          0.442 * rock_cover +
          1.764 * (basal_cover + cryptogams_cover) +
          2.068 * slope_steepness)

    ft = pow(10, ft)

    # Implement the new equations to calculate ke.
    keb = None
    if soil_texture == 'sand':
        keb = 24 * math.exp(0.3483 * (basal_cover + litter_cover))
    elif soil_texture == 'loamy sand':
        keb = 10 * math.exp(0.8755 * (basal_cover + litter_cover))
    elif soil_texture == 'sandy loam':
        keb = 5 * math.exp(1.1632 * (basal_cover + litter_cover))
    elif soil_texture == 'loam':
        keb = 2.5 * math.exp(1.5686 * (basal_cover + litter_cover))
    elif soil_texture == 'silt loam':
        keb = 1.2 * math.exp(2.0149 * (basal_cover + litter_cover))
    elif soil_texture == 'silt':
        keb = 1.2 * math.exp(2.0149 * (basal_cover + litter_cover))
    elif soil_texture == 'sandy clay loam':
        keb = 0.80 * math.exp(2.1691 * (basal_cover + litter_cover))
    elif soil_texture == 'clay loam':
        keb = 0.50 * math.exp(2.3026 * (basal_cover + litter_cover))
    elif soil_texture == 'silty clay loam':
        keb = 0.40 * math.exp(2.1691 * (basal_cover + litter_cover))
    elif soil_texture == 'sandy clay':
        keb = 0.30 * math.exp(2.1203 * (basal_cover + litter_cover))
    elif soil_texture == 'silty clay':
        keb = 0.25 * math.exp(1.7918 * (basal_cover + litter_cover))
    elif soil_texture == 'clay':
        keb = 0.2 * math.exp(1.3218 * (basal_cover + litter_cover))

    assert keb is not None

    # Calculate weighted KE
    # this array will be used to store the canopy cover, ke, and kss values for the cover types that are not 0
    vegetation_cover = [dict(cover=shrubs_cover, ke=keb*1.2),
                        dict(cover=sodgrass_cover, ke=keb*0.8),
                        dict(cover=bunchgrass_cover, ke=keb*1.0),
                        dict(cover=forbs_cover, ke=keb*1.0)]

    # Calculate the weighted ke and kss values based on the selected vegetation types by the user
    weighted_ke = 0
    # calculate weighted ke and kss values for the vegetation types that have non-zero values
    if totalcover > 0:
        for sel_cover in vegetation_cover:
            weighted_ke = weighted_ke + (sel_cover['cover']/totalcover) * sel_cover['ke']
    else:
        weighted_ke = keb

    # kss variables
    # 1)
    #   a) CALCULATE KSS FOR EACH VEGETATION COMMUNITY USING TOTAL FOLIAR COVER
    #      A)   BUNCH GRASS
    if total_ground_cover < 0.475:
        kss_seg_bunch = 4.154 + 2.5535 * slope_steepness - 2.547 * total_ground_cover - 0.7822 * totalcover
        kss_seg_bunch = pow(10, kss_seg_bunch)

        kss_seg_sod = 4.2169 + 2.5535 * slope_steepness - 2.547 * total_ground_cover - 0.7822 * totalcover
        kss_seg_sod = pow(10, kss_seg_sod)

        kss_seg_shrub = 4.2587 + 2.5535 * slope_steepness - 2.547 * total_ground_cover - 0.7822 * totalcover
        kss_seg_shrub = pow(10, kss_seg_shrub)

        kss_seg_forbs = 4.1106 + 2.5535 * slope_steepness - 2.547 * total_ground_cover - 0.7822 * totalcover
        kss_seg_forbs = pow(10, kss_seg_forbs)

        kss_seg_shrub_0 = 4.2587 + 2.5535 * slope_steepness - 2.547 * total_ground_cover
        kss_seg_shrub_0 = pow(10, kss_seg_shrub_0)
    else:
        kss_seg_bunch = 3.1726975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover - 0.7822 * totalcover
        kss_seg_bunch = pow(10, kss_seg_bunch)

        kss_seg_sod = 3.2355975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover - 0.7822 * totalcover
        kss_seg_sod = pow(10, kss_seg_sod)

        kss_seg_shrub = 3.2773975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover - 0.7822 * totalcover
        kss_seg_shrub = pow(10, kss_seg_shrub)

        kss_seg_forbs = 3.1292975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover - 0.7822 * totalcover
        kss_seg_forbs = pow(10, kss_seg_forbs)

        kss_seg_shrub_0 = 3.2773975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover
        kss_seg_shrub_0 = pow(10, kss_seg_shrub_0)

    # 2) CALCULATE AVERAGE KSS WHEN TOTAL FOLIAR COVER IS CLOSE TO 0
    kss_average = None
    if 0 > totalcover < 0.02:
        kss_average = totalcover/0.02 * ((shrubs_cover/totalcover) * kss_seg_shrub +
                                         (sodgrass_cover/totalcover) * kss_seg_sod +
                                         (bunchgrass_cover/totalcover) * kss_seg_bunch +
                                         (forbs_cover/totalcover) * kss_seg_forbs) + \
                      (0.02 - totalcover)/0.02 * kss_seg_shrub_0
    elif totalcover >= 0.02:
        kss_average = (shrubs_cover/totalcover) * kss_seg_shrub + \
                       (sodgrass_cover/totalcover) * kss_seg_sod + \
                       (bunchgrass_cover/totalcover) * kss_seg_bunch + \
                       (forbs_cover/totalcover) * kss_seg_forbs

    # 3) CALCULATE KSS USED FOR RHEM (with canopy cover == 0 and canopy cover > 0)
    if totalcover == 0:
        if total_ground_cover < 0.475:
            kss_final = 4.2587 + 2.5535 * slope_steepness - 2.547 * total_ground_cover
            kss_final = pow(10, kss_final)
        else:
            kss_final = 3.2773975 + 2.5535 * slope_steepness - 0.4811 * total_ground_cover
            kss_final = pow(10, kss_final)
    else:
        if total_ground_cover < 0.475:
            kss_final = total_ground_cover / 0.475 * kss_average + (0.475 - total_ground_cover) / 0.475 * kss_seg_shrub
        else:
            kss_final = kss_average

    kss_final *= 1.3 * 2.0
    chezy = pow(((8 * 9.8) / ft), 0.5)
    rchezy = pow(((8 * 9.8) / ft), 0.5)

    slope_length *= 2.5

    # Set working directory and file name
    fn = _join(out_dir, '{}.par'.format(scn_name))

    # Write to soil log file
    with open(fn, 'w') as fp:
        fp.write(_par_template_loader().format(
            scn_name=scn_name,
            now=datetime.now,
            model_version=model_version,
            slope_length=slope_length,
            soil=soil,
            width=width,
            chezy=chezy,
            rchezy=rchezy,
            sl='\t,\t'.join(str(v) for v in sl),
            sx='\t,\t'.join(str(v) for v in sx),
            moisture_content=moisture_content,
            kss_final=kss_final,
            weighted_ke=weighted_ke))

    return fn


def make_hillslope_run(
    run_fn: str,
    par_fn: str,
    stm_fn: str,
    out_summary: str,
    scn_name: str,
) -> None:
    """Write an entry to the batch ``*.run`` file for RHEM CLI execution."""
    template = '{parameter_file}, {storm_file}, {output_summary}, "{scenario_name}",0,2,y,y,n,n,y'

    with open(run_fn, 'w') as fp:
        fp.write(template.format(parameter_file=par_fn, storm_file=stm_fn,
                                 output_summary=out_summary, scenario_name=scn_name))


def run_hillslope(topaz_id: str, runs_dir: str) -> tuple[bool, str, float]:
    """Execute the compiled RHEM binary for a single hillslope scenario.

    Returns:
        Tuple of (success flag, Topaz ID, runtime seconds).
    """
    t0 = time()
    run_fn = _join(runs_dir, 'hill_{}.run'.format(topaz_id))
    cmd = [os.path.abspath(_rhem), '-b', run_fn]

    assert _exists(_join(runs_dir, 'hill_{}.par'.format(topaz_id)))
    assert _exists(_join(runs_dir, 'hill_{}.stm'.format(topaz_id)))
    assert _exists(run_fn)

    _log = open(_join(runs_dir, 'hill_{}.err'.format(topaz_id)), 'w')

    p = subprocess.Popen(cmd, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait(timeout=200)
    _log.close()

    return True, topaz_id, time() - t0

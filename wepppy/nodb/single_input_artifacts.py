"""Validate opted-in, generated consumer files before WEPP execution."""
from pathlib import Path

from wepppy.nodb.single_input_policy import single_input_uploads_enabled
from wepppy.wepp.management.managements import Management
from wepppy.wepp.single_input import read_uploaded_management, validate_soil_text
from wepppy.wepp.soils.utils import WeppSoilUtil


def validate_prepared_single_inputs(wepp, translator):
    if not single_input_uploads_enabled(wepp):
        return
    landuse = wepp.landuse_instance
    soils = wepp.soils_instance
    watershed = wepp.watershed_instance
    runs = Path(wepp.runs_dir)
    for topaz_id in watershed.subs_summary:
        wepp_id = translator.wepp(top=int(topaz_id))
        expected = int(watershed.mofe_nsegments[str(topaz_id)]) if wepp.multi_ofe else 1
        if not 1 <= expected <= 32:
            raise ValueError('WEPP supports 1–32 OFEs per hillslope for this project.')
        stem = f'p{wepp_id}'
        slope = [line.strip() for line in (runs / (stem + '.slp')).read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        soil = WeppSoilUtil(str(runs / (stem + '.sol')), compute_erodibilities=False, compute_conductivity=False)
        management = Management(Key=None, ManagementFile=stem + '.man', ManagementDir=str(runs),
                                Description='Prepared input', Color=(0, 0, 0, 255), NativeScenarioReferences=True)
        if int(slope[1]) != expected or len(soil.obj['ofes']) != expected or management.nofe != expected:
            raise ValueError(f'Slope, management and soil OFE counts disagree for hillslope {topaz_id}.')
        for name, maximum in [('plants', 20), ('ops', 32), ('inis', 32), ('surfs', 30),
                              ('contours', 32), ('drains', 32), ('years', 32)]:
            if len(getattr(management, name)) > maximum:
                raise ValueError(f'Prepared {name} exceed the supported native reader limit.')
        if int(landuse.mode) == 5:
            read_uploaded_management(runs / (stem + '.man'), max_ofes=32)
        if int(soils.mode) == 5:
            validate_soil_text((runs / (stem + '.sol')).read_text(), max_ofes=32)

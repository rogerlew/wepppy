
from wepppy.nodb.mods.omni import Omni, OmniScenario

if __name__ == '__main__':
    runid = 'rlew-confirmed-complementarity'

    omni = Omni.getInstanceFromRunID(runid)
    omni.clear_contrasts()

    if not hasattr(omni, '_contrast_names'):
        omni._contrast_names = None

    control_scenario_def = dict(type=OmniScenario.SBSmap)
    contrast_scenario_defs = [
        dict(type=OmniScenario.Mulch, ground_cover_increase='60%', base_scenario=OmniScenario.SBSmap),
        dict(type=OmniScenario.Mulch, ground_cover_increase='30%', base_scenario=OmniScenario.SBSmap),
        dict(type=OmniScenario.Mulch, ground_cover_increase='15%', base_scenario=OmniScenario.SBSmap)
    ]

    for contrast_scenario_def in contrast_scenario_defs:
        omni.build_contrasts(control_scenario_def, contrast_scenario_def,
                            obj_param='Soil_Loss_kg',
                            contrast_cumulative_obj_param_threshold_fraction=1.0)
        
    #from pprint import pprint
    #pprint(omni.contrasts)

    omni.run_omni_contrasts()

from pprint import pprint

from wepppy.nodb import Omni

omni = Omni.getInstance()

omni.build_contrasts(control_scenario='uniform_high', contrast_scenario='thinning')

pprint(omni.contrasts)


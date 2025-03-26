from pprint import pprint

from wepppy.nodb import Omni

omni = Omni.getInstance()

pprint(omni.get_soil_erosion_from_gpkg())
pprint(omni.get_soil_erosion_from_gpkg(scenario='uniform_high'))
pprint(omni.get_soil_erosion_from_gpkg(scenario='thinning'))


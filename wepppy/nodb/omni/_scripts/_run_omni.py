from wepppy.nodb import Omni
omni = Omni.getInstance()
omni.scenarios = ['uniform_low', 'uniform_high', 'uniform_moderate', 'thinning']
omni.run_omni()

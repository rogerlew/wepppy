if __name__ == "__main__":
    from wepppy.nodb.mods.ash_transport import Ash
    from wepppy.nodb.mods.ash_transport.ash_multi_year_model import *

    wd = '/geodata/weppcloud_runs/squab-salami'
    # wd = '/geodata/weppcloud_runs/undisciplined-camshaft'
    ash = Ash.getInstance(wd)
    ash._anu_black_ash_model_pars = BlackAshModel()
    ash._anu_white_ash_model_pars = WhiteAshModel()
    ash.run_ash()

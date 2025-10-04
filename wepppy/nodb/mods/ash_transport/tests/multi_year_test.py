from os.path import join as _join

if __name__ == "__main__":
    from pprint import pprint
    from wepppy.nodb.core import Ron
    from wepppy.nodb.mods.ash_transport import Ash, AshPost
    from wepppy.nodb.mods.ash_transport.ash_multi_year_model import *
    """
https://dev.wepp.cloud/weppcloud/runs/srivas42-mountainous-misogyny/disturbed-anu-ash/
https://dev.wepp.cloud/weppcloud/runs/srivas42-polymorphous-wok/disturbed9002/
https://dev.wepp.cloud/weppcloud/runs/srivas42-domed-nuance/disturbed-anu-ash/
https://dev.wepp.cloud/weppcloud/runs/srivas42-indecorous-misanthropy/disturbed-anu-ash/
https://dev.wepp.cloud/weppcloud/runs/srivas42-perpendicular-gong/disturbed-anu-ash/
https://dev.wepp.cloud/weppcloud/runs/srivas42-anxious-gannet/disturbed-anu-ash/
    """
    import sys

    #wd = '/geodata/weppcloud_runs/srivas42-polymorphous-wok'
    #wd = '/geodata/weppcloud_runs/undisciplined-camshaft2'

    wd = sys.argv[1]

    if os.path.exists(_join(wd, 'ash.nodb')):
        os.remove(_join(wd, 'ash.nodb'))

    if os.path.exists(_join(wd, 'ash.nodb.lock')):
        os.remove(_join(wd, 'ash.nodb.lock'))

    if os.path.exists(_join(wd, 'ashpost.nodb')):
        os.remove(_join(wd, 'ashpost.nodb'))

    if os.path.exists(_join(wd, 'ashpost.nodb.lock')):
        os.remove(_join(wd, 'ashpost.nodb.lock'))

    ash = Ash(wd, Ron.getInstance(wd).config_stem + '.cfg')

    ash._anu_black_ash_model_pars = BlackAshModel()
    ash._anu_white_ash_model_pars = WhiteAshModel()
    ash.run_ash(fire_date='8/4',
                ini_white_ash_depth_mm=15.0,
                ini_black_ash_depth_mm=15.0)


    ashpost = AshPost.getInstance(wd)
    pprint(ashpost.burn_class_return_periods)

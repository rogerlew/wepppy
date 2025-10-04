from os.path import join as _join

if __name__ == "__main__":
    from wepppy.nodb.core import Ron
    from wepppy.nodb.mods.ash_transport import AshPost
    from wepppy.nodb.mods.ash_transport.ash_multi_year_model import *

    wd = '/geodata/weppcloud_runs/srivas42-mountainous-misogyny'
    #wd = '/geodata/weppcloud_runs/undisciplined-camshaft2'

    ashpost = AshPost.getInstance(wd)
    ashpost.run_post()
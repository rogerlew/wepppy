from os.path import exists
from os.path import join as _join
import os

from wepppy.nodb import Wepp


for run_id in ['mdobre-red-workday',
               'mdobre-pint-size-objectivity',
               'mdobre-cross-eyed-semblance',
               'mdobre-scarce-belch',
               'mdobre-overage-catenary',
               'mdobre-autonomic-ostrich',
               'mdobre-inshore-nutrition',
               'mdobre-taut-grist',
               'mdobre-fifty-pressing',
               'mdobre-womanly-ascot'
               ]:
    wd = f'/geodata/weppcloud_runs/{run_id}'
    print(wd)

    with open(_join(wd, 'wepp/runs/pmetpara.txt')) as fp:
        print(wd)
        print(fp.read())
        print()

    if exists(_join(wd, 'READONLY')):
        os.remove(_join(wd, 'READONLY'))

    wepp = Wepp.getInstance(wd)
    wepp.set_phosphorus_opts(surf_runoff=0.003,
                    lateral_flow=0.004,
                    baseflow=0.005,
                    sediment=1000)


    print('clean...')

    wepp.clean()

    print('prep_hillslopes...')
    wepp.prep_hillslopes()

    print('run_hillslopes...')
    wepp.run_hillslopes()

    wepp = Wepp.getInstance(wd)

    print('prep_watershed...')
    wepp.prep_watershed()

    print('run_watershed...')
    wepp.run_watershed()


    with open(_join(wd, 'READONLY'), 'w') as fp:
        fp.write("")

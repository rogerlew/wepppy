import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import sys
import shutil
from glob import glob
from wepppy.nodb import Ron, Wepp
from wepppy.wepp.stats import HillSummary, ChannelSummary, OutletSummary, SedimentDelivery

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    prefix = 'lt202212'
    outdir = '/home/mariana/%s_csvs' % prefix

    if _exists(outdir):
        res = input('Outdir exists, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    scenarios = [
#                 'lt_202212*SimFire.fccsFuels_obs_cli',
#                 'lt_202212*SimFire.landisFuels_obs_cli',
#                 'lt_202212*SimFire.landisFuels_fut_cli_A2',
                 'lt_202212*CurCond',
#                 'lt_202212*PrescFire',
#                 'lt_202212*LowSev',
#                 'lt_202212*ModSev',
#                 'lt_202212*HighSev',
#                 'lt_202212*Thinn96',
#                 'lt_202212*Thinn93',
#                 'lt_202212*Thinn85'
                ]

    wds = []
    for wc in scenarios:
        wds.extend(glob(_join('/geodata/weppcloud_runs', '*{}*'.format(wc))))
    wds = [wd for wd in wds if os.path.isdir(wd)]

    fp_hill = open(_join(outdir, '%s_hill_summary.csv' % prefix), 'w')
    fp_chn = open(_join(outdir, '%s_chn_summary.csv' % prefix), 'w')
    fp_out = open(_join(outdir, '%s_out_summary.csv' % prefix), 'w')
    fp_sd = open(_join(outdir, '%s_sed_del_summary.csv' % prefix), 'w')

    for i, wd in enumerate(wds):
        if not os.path.isdir(wd):
            continue
        print(wd)
        write_header = i == 0

        ron = Ron.getInstance(wd)
        subcatchments_summary = {_d['meta']['topaz_id']: _d for _d in ron.subs_summary()}
        channels_summary = {_d['meta']['topaz_id']: _d for _d in ron.chns_summary()}

        name = ron.name

        _wd = _split(wd)[-1]
        for scn in scenarios:
            lt_date, scn_desc = scn.split('*')
            _wd = _wd.replace(lt_date, '')
            if scn_desc in _wd:
                scenario = scn_desc
                _wd = _wd.replace(scn_desc, '')
        watershed = _wd[1:-1]

        run_descriptors = [('ProjectName', name), ('Scenario', scenario), ('Watershed', watershed)]

        loss = Wepp.getInstance(wd).report_loss()

        hill_rpt = HillSummary(loss, class_fractions=True, fraction_under=0.016, subs_summary=subcatchments_summary)

        chn_rpt = ChannelSummary(loss, chns_summary=channels_summary)
        out_rpt = OutletSummary(loss, fraction_under=0.016)
        sed_del = SedimentDelivery(wd)

        hill_rpt.write(fp_hill, write_header=write_header, run_descriptors=run_descriptors)
        chn_rpt.write(fp_chn, write_header=write_header, run_descriptors=run_descriptors)
        out_rpt.write(fp_out, write_header=write_header, run_descriptors=run_descriptors)
        sed_del.write(fp_sd, write_header=write_header, run_descriptors=run_descriptors)

    fp_hill.close()
    fp_chn.close()
    fp_out.close()
    fp_sd.close()

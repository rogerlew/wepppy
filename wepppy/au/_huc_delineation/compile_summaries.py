import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import sys
import shutil
from glob import glob
from wepppy.nodb import Ron, Wepp, Ash, AshPost
from wepppy.wepp.stats import HillSummary, ChannelSummary, OutletSummary, SedimentDelivery


if __name__ == "__main__":
    prefix = 'au_2020_gwc2'
    outdir = '/geodata/au/%s_csvs' % prefix

    if _exists(outdir):
        res = input('Outdir exists, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    wds = glob(_join('/geodata/weppcloud_runs/au', '*'))
    wds = [wd for wd in wds if os.path.isdir(wd)]

    fp_hill = open(_join(outdir, '%s_hill_summary.csv' % prefix), 'w')
    fp_chn = open(_join(outdir, '%s_chn_summary.csv' % prefix), 'w')
    fp_out = open(_join(outdir, '%s_out_summary.csv' % prefix), 'w')
    fp_sd = open(_join(outdir, '%s_sed_del_summary.csv' % prefix), 'w')

    write_header = True
    for i, wd in enumerate(wds):
        if not os.path.isdir(wd):
            continue

        print(wd)

        if not _exists(_join(wd, 'wepp/output/loss_pw0.txt')):
            continue

        ron = Ron.getInstance(wd)
        subcatchments_summary = {_d['meta']['topaz_id']: _d for _d in ron.subs_summary()}
        channels_summary = {_d['meta']['topaz_id']: _d for _d in ron.chns_summary()}

        ash_out = None
        try:
            ash = Ash.getInstance(wd)
            ash_post = AshPost.getInstance(wd)
        except FileNotFoundError:
            ash = ash_post = ash_out = None

        if ash_post is not None:
            try:
                ash_out = ash_post.ash_out
            except:
                ash_out = None
                raise

        name = ron.name

        # _wd = _split(wd)[-1].split('_')
        # if _wd[3][0] in 'BWG' or _wd[3].startswith('Me'):
        #     indx = 4
        # else:
        #     indx = 3

        scenario = 'sbs'  # '_'.join(_wd[indx:])
        watershed = _split(wd)[-1]  # '_'.join(_wd[:indx])

        run_descriptors = [('ProjectName', name), ('Scenario', scenario), ('Watershed', watershed)]

        loss = Wepp.getInstance(wd).report_loss()

        hill_rpt = HillSummary(loss, subs_summary=subcatchments_summary, ash_out=ash_out)

        chn_rpt = ChannelSummary(loss, chns_summary=channels_summary)
        out_rpt = OutletSummary(loss)
        sed_del = SedimentDelivery(wd)

        hill_rpt.write(fp_hill, write_header=write_header, run_descriptors=run_descriptors)
        chn_rpt.write(fp_chn, write_header=write_header, run_descriptors=run_descriptors)
        out_rpt.write(fp_out, write_header=write_header, run_descriptors=run_descriptors)
        sed_del.write(fp_sd, write_header=write_header, run_descriptors=run_descriptors)

        if write_header:
            write_header = False

    fp_hill.close()
    fp_chn.close()
    fp_out.close()
    fp_sd.close()

import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import sys
import shutil
from glob import glob
from wepppy.nodb import Ron, Wepp
from wepppy.wepp.reports import (
    ChannelSummaryReport,
    HillSummaryReport,
    OutletSummaryReport,
    SedimentDelivery,
)

from wepppy.wepp.management import pmetpara_prep

from Cedar_runs_sim23 import projects

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    prefix = 's2'

    outdir = '/home/roger/%s_csvs' % prefix

    if _exists(outdir):
        res = input('Outdir exists, Delete outdir?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    fp_hill = open(_join(outdir, '%s_hill_summary.csv' % prefix), 'w')
    fp_chn = open(_join(outdir, '%s_chn_summary.csv' % prefix), 'w')
    fp_out = open(_join(outdir, '%s_out_summary.csv' % prefix), 'w')
    fp_sd = open(_join(outdir, '%s_sed_del_summary.csv' % prefix), 'w')

    i = 0
    for proj in projects:
        if proj['scenario'] != prefix:
            continue

        wd = _join('/geodata/weppcloud_runs', proj['wd'])

        print(wd)

        write_header = i == 0

        ron = Ron.getInstance(wd)
        subcatchments_summary = {_d['meta']['topaz_id']: _d for _d in ron.subs_summary()}
        channels_summary = {_d['meta']['topaz_id']: _d for _d in ron.chns_summary()}

        run_descriptors = [('Watershed', proj['watershed']),
                           ('Scenario', proj['scenario']),
                           ('Condition', proj['condition'])]

        loss = Wepp.getInstance(wd).report_loss()

        hill_rpt = HillSummaryReport(loss, class_fractions=True, subs_summary=subcatchments_summary)

        chn_rpt = ChannelSummaryReport(loss, chns_summary=channels_summary)
        out_rpt = OutletSummaryReport(loss)
        sed_del = SedimentDelivery(wd)

        hill_rpt.write(fp_hill, write_header=write_header, run_descriptors=run_descriptors)
        chn_rpt.write(fp_chn, write_header=write_header, run_descriptors=run_descriptors)
        out_rpt.write(fp_out, write_header=write_header, run_descriptors=run_descriptors)
        sed_del.write(fp_sd, write_header=write_header, run_descriptors=run_descriptors)

        i += 1

    fp_hill.close()
    fp_chn.close()
    fp_out.close()
    fp_sd.close()

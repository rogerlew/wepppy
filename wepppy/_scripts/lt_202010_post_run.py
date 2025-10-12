from wepppy.weppcloud import combined_watershed_viewer_generator
import os
import subprocess
import shutil

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from wepppy.nodb import Ron, Wepp
from wepppy.wepp.reports import (
    ChannelSummaryReport,
    HillSummaryReport,
    OutletSummaryReport,
    SedimentDelivery,
)

prefix = 'lt_202010'

scenarios = [('SimFire.fccsFuels_obs_cli', 'Wildfire – current conditions - observed climates'),
             ('SimFire.landisFuels_obs_cli', 'Wildfire – future conditions - observed climates'),
             ('SimFire.landisFuels_fut_cli_A2', 'Wildfire – future conditions - future climates'),
             ('CurCond', 'Current Conditions and Managements'),
             ('PrescFire', 'Uniform Prescribed Fire'),
             ('LowSev', 'Uniform Low Severity Fire'),
             ('ModSev', 'Uniform Moderate Severity Fire'),
             ('HighSev', 'Uniform High Severity Fire'),
             ('Thinn96', 'Uniform Thinning (96% Cover)'),
             ('Thinn93', 'Uniform Thinning (Cable 93% Cover)'),
             ('Thinn85', 'Uniform Thinning (Skidder 85% Cover)')]

run_li_template = '''\
<li class="list-group-item"><a href="../runs/{runid}/{cfg}/">{watershed}</a></li>'''

run_wepp_template = '''\
    <h3>{title}</h3>
    <div style="margin-left: 1.5em;">
        <h4>Delineate new watershed</h4>
        <div><a href="../create/{cfg}">Run WEPP</a></div>
        <div style="height: 1em;"></div>
        <h4>Pre-delineated watersheds</h4>
        <div><a href="#run-{scn_id}-man" data-toggle="collapse">Select Watershed</a>
        <div id="run-{scn_id}-man" class="collapse">
        <ul class="list-group">
            {runs_list}
        </ul>
        </div>
        </div>
    </div>
    <div style="height: 1em;"></div>\n'''


def identify_scenario_watershed(runid):
    global prefix

    _scn = None
    for scn, title in scenarios:
        if scn in runid:
            _scn = scn
            break

    if _scn is None:
        raise ValueError

    watershed = runid.replace(prefix + '_', '').replace('_' + _scn, '')

    if watershed.endswith('/'):
        watershed = watershed[:-1]

    return _scn, watershed


with open(prefix + '_runs.txt') as fp:
    runs = fp.read().split()
    runs = [run.strip() for run in runs]

# build the combined watershed generator urls
fp = open(prefix + '_ws_viewer.htm', 'w')
fp2 = open(prefix + '_runs.htm', 'w')

shps_outdir = '/home/roger/{prefix}_shps'.format(prefix=prefix)
csv_outdir = '/home/roger/{prefix}_csvs'.format(prefix=prefix)

if _exists(shps_outdir):
    shutil.rmtree(shps_outdir)
os.mkdir(shps_outdir)

if _exists(csv_outdir):
    shutil.rmtree(csv_outdir)
os.mkdir(csv_outdir)

for i, (scn, title) in enumerate(scenarios):
    scn_runs = []
    for run in runs:
        if scn in run:
            scn_runs.append(run)

    print(scn, len(scn_runs))

    js = combined_watershed_viewer_generator(runids=scn_runs, title=title, asjson=True)

    with open('/workdir/wepppy/wepppy/weppcloud/static/mods/lt/results/{prefix}_{scn}.json'
              .format(prefix=prefix, scn=scn), 'w') as fp3:
        fp3.write(js)

    fp.write("""        <h3>{title}</h3>\n""".format(title=title))
    fp.write("""        <a href='https://wepp1.nkn.uidaho.edu/weppcloud/combined_ws_viewer/"""
             """?data_uri=../static/mods/lt/results/{prefix}_{scn}.json'>View {scn}</a>\n\n"""
             .format(prefix=prefix, scn=scn))

    runs_list = []
    for scn_run in scn_runs:
        wd = _join('/geodata/weppcloud_runs', scn_run)
        ron = Ron.getInstance(wd)
        cfg = ron.config_stem
        _scn, watershed = identify_scenario_watershed(scn_run)

        runs_list.append(run_li_template.format(runid=scn_run, cfg=cfg, watershed=watershed.replace('_', ' ')))

    fp2.write(run_wepp_template.format(title=title, cfg=cfg, scn_id=i, runs_list='\n'.join(runs_list)))

    # merge the arcmaps
    channels = []
    subcatchments = []

    for scn_run in scn_runs:
        wd = _join('/geodata/weppcloud_runs', scn_run)

        chn = _join(wd, 'export', 'arcmap', 'channels.shp')
        assert _exists(chn), chn
        channels.append(chn)

        sub = _join(wd, 'export', 'arcmap', 'subcatchments.shp')
        assert _exists(sub), sub
        subcatchments.append(sub)

    print(channels)
    print(sub)

    argv = ['python3', '/workdir/wepppy/wepppy/all_your_base/ogrmerge.py', '-o', '%s/%s_channels.shp' % (shps_outdir, scn),
            '-single'] + channels
    print(argv)
    subprocess.call(argv)

    argv = ['python3', '/workdir/wepppy/wepppy/all_your_base/ogrmerge.py', '-o', '%s/%s_subcatchments.shp' % (shps_outdir, scn),
            '-single'] + subcatchments
    print(argv)
    subprocess.call(argv)

fp.close()
fp2.close()

print('merged shps are in', shps_outdir)

fp_hill = open(_join(csv_outdir, '%s_hill_summary.csv' % prefix), 'w')
fp_chn = open(_join(csv_outdir, '%s_chn_summary.csv' % prefix), 'w')
fp_out = open(_join(csv_outdir, '%s_out_summary.csv' % prefix), 'w')
fp_sd = open(_join(csv_outdir, '%s_sed_del_summary.csv' % prefix), 'w')

for i, runid in enumerate(runs):
    wd = _join('/geodata/weppcloud_runs', runid)
    if not os.path.isdir(wd):
        continue
    print(wd)
    write_header = i == 0

    ron = Ron.getInstance(wd)
    subcatchments_summary = {_d['meta']['topaz_id']: _d for _d in ron.subs_summary()}
    channels_summary = {_d['meta']['topaz_id']: _d for _d in ron.chns_summary()}

    name = ron.name

    scenario, watershed = identify_scenario_watershed(runid)

    run_descriptors = [('ProjectName', name), ('Scenario', scenario), ('Watershed', watershed)]

    loss = Wepp.getInstance(wd).report_loss()

    hill_rpt = HillSummaryReport(loss, class_fractions=True, fraction_under=0.016, subs_summary=subcatchments_summary)

    chn_rpt = ChannelSummaryReport(loss, chns_summary=channels_summary)
    out_rpt = OutletSummaryReport(loss, fraction_under=0.016)
    sed_del = SedimentDelivery(wd)

    hill_rpt.write(fp_hill, write_header=write_header, run_descriptors=run_descriptors)
    chn_rpt.write(fp_chn, write_header=write_header, run_descriptors=run_descriptors)
    out_rpt.write(fp_out, write_header=write_header, run_descriptors=run_descriptors)
    sed_del.write(fp_sd, write_header=write_header, run_descriptors=run_descriptors)

fp_hill.close()
fp_chn.close()
fp_out.close()
fp_sd.close()

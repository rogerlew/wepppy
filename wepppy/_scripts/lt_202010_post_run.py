from wepppy.weppcloud import combined_watershed_viewer_generator

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

with open('lt_202010_runs.txt') as fp:
    runs = fp.read().split()
    runs = [run.strip() for run in runs]

fp = open('lt_202010_ws_viewer.htm', 'w'
          )
for scn, title in scenarios:
    scn_runs = []
    for run in runs:
        if scn in run:
            scn_runs.append(run)

    print(scn, len(scn_runs))

    url = combined_watershed_viewer_generator(runids=scn_runs, title=title)

    fp.write("""        <h3>{title}</h3>\n""".format(title=title))
    fp.write("""        <a href='{url}'>View {scn}</a>\n\n""".format(url=url, scn=scn))

fp.close()

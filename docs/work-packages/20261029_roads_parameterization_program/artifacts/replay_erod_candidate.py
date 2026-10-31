"""Run unchanged development inputs with the isolated EROD U1 pair."""
from pathlib import Path
import json,sys
import depend_bounded_replay as replay
P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
replay.ROOT=P/'erod-support-u1';replay.BINARY=replay.ROOT/'bin/wepp'

def main():
    if sys.argv[1]!='seeds':
        replay.main();return
    case='site-1718465-outunrut-gravel-low-erosion_road_cap-project'
    g1=P/'depend-bounded-g1'
    sources={'ordinary':g1/'roads/site-1718465-inveg-paved-high-erosion_road_cap-project',
             'buffer_cap':g1/'downstream-buffer_cap'/case,'buffer_control':g1/'roads'/case,
             'depend_failure':next((g1/'fixture-fill_fixed').iterdir())}
    rows=[]
    for label,source in sources.items():
        old=json.loads((source/'record.json').read_text())
        row=replay.execute((str(source),old,'seed-'+label,replay.digest(replay.BINARY)))
        rows.append(row);print(label,row['returncode'],row['physical_pass'],row['changed_outputs'],flush=True)
    replay.save(replay.ROOT/'seed-results.json',rows)
if __name__=='__main__':main()

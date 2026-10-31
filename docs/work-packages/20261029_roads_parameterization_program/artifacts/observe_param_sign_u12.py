"""Repeat the retained U11 observer on the combined U12 candidate, exact parity required."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import param_sign_ablation as ablation
import replay_particle_capacity_u11 as replay
P=ablation.P
ROOT=P/'param-sign-observe-u12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parent=P/'param-continuity-observe-u11'
    shutil.copytree(parent/'build',ROOT/'build')
    source=ROOT/'build/src';p=source/'param.for'
    text=p.read_text();assert text.count(ablation.OLD)==2
    p.write_text(text.replace(ablation.OLD,ablation.NEW))
    with (ROOT/'build.log').open('w') as log:
        subprocess.run(['make','-j4','FC=/usr/bin/gfortran','LINKER=/usr/bin/gfortran','wepp'],cwd=source,env={'PATH':'/usr/bin:/bin'},stdout=log,stderr=subprocess.STDOUT,check=True)
    (ROOT/'build.json').write_text(json.dumps(dict(parent=str(parent),param_sha256=sha(p),binary_sha256=sha(source/'wepp'),script_sha256=sha(Path(__file__))),indent=2)+'\n')
    candidate=P/'param-sign-u12-combined'
    replay.ROOT=ROOT;replay.BINARY=source/'wepp'
    replay.SEEDS={label:next((candidate/('seed-'+label)).glob('*/record.json')).parent for label in ['ordinary','buffer_cap','buffer_control','depend_failure']}
    replay.main()
if __name__=='__main__':main()

"""Observe initialization without changing model state; require exact raw parity."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/hydraulic-init-r3')
NATIVE = Path('/workdir/wepp-forest-release-20261009')
COMMIT = '6112b68bce0e21a77f510bde5c24af067a47a647'
MATRIX = Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-matrix840/matrix-v1')
PARENT = ROOT.parent
RELEASE = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
RELEASE_SHA = '1d07f5e47692a543e653f449feea23cf298093a9fd664d7a01a1b71dc5e01531'
MATERIALS = ('1718465','2711184','2711250','1718510','1856573','53949','1718494')
FIELDS = 'bd_kg_m3 om_fraction porosity rock_correction fc wp conductivity_m_s available_water_m upper_storage_m layer_thickness_m layer_bottom_m'.split()


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2) + '\n')


def build():
    ROOT.mkdir(exist_ok=False)
    builddir = ROOT / 'build'; builddir.mkdir()
    archive = ROOT / 'source.tar'
    with archive.open('wb') as out:
        subprocess.run(['git','-C',str(NATIVE),'archive',COMMIT,'src','fpm-src'],stdout=out,check=True)
    subprocess.run(['tar','xf',str(archive),'-C',str(builddir)],check=True)
    patches = {}
    for name, condition, label in [('scon.for',None,'SCON'),('watbal.for','iflag.eq.0','WATBAL_INIT')]:
        file = builddir/'src'/name; old = file.read_text()
        body = f'''c     Research observation only; no state assignment.
      do i = 1, nsl(iplane)
        write(6,'(A,2I6,11ES22.12)') 'ROAD_INIT_{label}',
     1    iplane,i,bd(i,iplane),orgmat(i,iplane),por(i,iplane),
     1    cpm(i,iplane),thetfc(i,iplane),thetdr(i,iplane),
     1    ssc(i,iplane),st(i,iplane),ul(i,iplane),dg(i,iplane),
     1    solthk(i,iplane)
      end do
'''
        if condition:
            body = f'      if ({condition}) then\n' + body + '      end if\n'
        assert old.count('      return\n') >= 1
        prefix, suffix = old.rsplit('      return\n', 1)
        patched = prefix + body + '      return\n' + suffix
        if name == 'watbal.for':
            patched = patched.replace("      include 'ccons.inc'", "      include 'ccons.inc'\n      include 'csolva1.inc'")
            marker = '         call watbal_hourly(lunp,luns,lunw,nowcrp,elevm)\n'
            assert patched.count(marker) == 1
            patched = patched.replace(marker, marker + body)
        file.write_text(patched)
        patches[name] = dict(original_sha256=hashlib.sha256(old.encode()).hexdigest(),observed_sha256=sha(file))
    env = dict(os.environ, PATH='/usr/bin:/bin:'+os.environ['PATH'])
    with (ROOT/'build.log').open('w') as out:
        subprocess.run(['make','-j4','FC=/usr/bin/gfortran','LINKER=/usr/bin/gfortran','wepp'],cwd=builddir/'src',env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
    binary = builddir/'src/wepp'
    dump(ROOT/'build.json',dict(source_commit=COMMIT,source_archive_sha256=sha(archive),patches=patches,
         binary=str(binary),binary_sha256=sha(binary),compiler=subprocess.check_output(['/usr/bin/gfortran','--version'],text=True).splitlines()[0],
         script_sha256=sha(Path(__file__)),observation_fields=FIELDS,build_log_sha256=sha(ROOT/'build.log')))
    print('Diagnostic binary built',flush=True)


def declare():
    buildinfo = json.loads((ROOT/'build.json').read_text())
    assert sha(Path(__file__)) == buildinfo['script_sha256'] and sha(RELEASE)==RELEASE_SHA
    old = json.loads((PARENT/'legacy-soil-control-r3/results.json').read_text())
    tasks = []
    for material in MATERIALS:
        item = next(row for row in old if row['case']['soil']==material)
        name = '-'.join(item['case'].values())
        for kind, source in [('generated',MATRIX/name),('legacy',PARENT/'legacy-soil-control-r3/matrix-v1'/name)]:
            record = json.loads((source/'record.json').read_text())
            assert record['physical_pass'] and record['binary_sha256']==RELEASE_SHA
            for filename, digest in record['inputs'].items():
                assert sha(source/'runs'/filename)==digest
            tasks.append(dict(material=material,kind=kind,case=item['case'],source=str(source),source_record_sha256=sha(source/'record.json')))
    declaration = dict(build=buildinfo,tasks=tasks,release_sha256=RELEASE_SHA,
         contract='14 complete-period observation replays, unchanged inputs. SCON end and WATBAL iflag=0 end; later daily state is not initialization. Require identical output file inventory and bytes to released baseline. No parameter/default changes.')
    dump(ROOT/'declaration.json',declaration);dump(HERE/'hydraulic-init-r3-declaration.json',declaration)
    shutil.copy2(__file__,ROOT/'executed-study.py')
    print('Declared 14 observation replays',flush=True)


def execute(task):
    source = Path(task['source']); old = json.loads((source/'record.json').read_text())
    assert sha(source/'record.json')==task['source_record_sha256']
    folder = ROOT/'cases'/(task['material']+'-'+task['kind']);runs=folder/'runs';output=folder/'output'
    runs.mkdir(parents=True,exist_ok=False);output.mkdir()
    for name,digest in old['inputs'].items():
        assert sha(source/'runs'/name)==digest
        shutil.copy2(source/'runs'/name,runs/name)
    declaration = json.loads((ROOT/'declaration.json').read_text());binary=Path(declaration['build']['binary'])
    assert sha(binary)==declaration['build']['binary_sha256']
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as out,(runs/'stderr').open('w') as err:
        result=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=out,stderr=err,timeout=300)
    assert result.returncode==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text()
    generated={f.name:sha(f) for f in output.iterdir() if f.is_file()}
    # Baseline record predates interchange-generated directories; retain raw files only.
    assert generated == old['outputs'], (task, set(generated)^set(old['outputs']))
    for name,digest in old['outputs'].items():assert sha(source/'output'/name)==digest
    states=[]
    for line in (runs/'stdout').read_text().splitlines():
        if line.startswith('ROAD_INIT_'):
            fields=line.split();assert len(fields)==14
            states.append(dict(stage=fields[0],ofe=int(fields[1]),layer=int(fields[2]),**dict(zip(FIELDS,map(float,fields[3:])))))
    assert {s['stage'] for s in states}=={'ROAD_INIT_SCON','ROAD_INIT_WATBAL_INIT'}
    assert {s['ofe'] for s in states}=={1,2,3}
    row=dict(task,inputs=old['inputs'],outputs=generated,raw_output_parity=True,states=states,soil_readback=old['soil_readback'],
             stdout_sha256=sha(runs/'stdout'),stderr_sha256=sha(runs/'stderr'))
    dump(folder/'record.json',row)
    return row


def run():
    declaration=json.loads((ROOT/'declaration.json').read_text())
    assert sha(Path(__file__))==declaration['build']['script_sha256']
    with ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(execute,declaration['tasks']))
    result=dict(replays=len(rows),exact_raw_output_matches=sum(row['raw_output_parity'] for row in rows),
                declaration_sha256=sha(ROOT/'declaration.json'),rows=rows)
    dump(ROOT/'results.json',result);dump(HERE/'hydraulic-init-r3-results.json',result)
    print('14/14 full-period exact output parity; initialization states retained',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('build','declare','run'))
    {'build':build,'declare':declare,'run':run}[parser.parse_args().action]()

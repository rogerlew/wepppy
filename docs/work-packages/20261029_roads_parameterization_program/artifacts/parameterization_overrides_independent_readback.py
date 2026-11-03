"""Independent raw PASS/ELEMENT readback for declared native override study."""
from pathlib import Path
from decimal import Decimal as D
import datetime
import hashlib
import importlib.util
import json
import math

ART = Path(__file__).resolve().parent
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def private(name):
    spec = importlib.util.spec_from_file_location('independent_' + name, ART/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    declaration = read(ROOT/'declaration-v5.json')
    results = read(ROOT/'results.json')
    tasks = {(r['context'],r['arm']):r for r in declaration['tasks']}
    assert len(results) == len(tasks) == 18
    for path, digest in declaration['dependencies'].items():
        assert sha(path) == digest, path
    checks = []
    for result in results:
        key = result['context'], result['arm']
        task = tasks[key]
        root = Path(task['root']); capsule = root/'wepp/roads'
        record = task['record']; native = read(root/'native-result.json')
        assert read(root/'result.json') == result
        for path, digest in record['prepared_files'].items():
            assert sha(capsule/'runs'/path) == digest
        assert len(native['output_sha256']) == 7
        for path, digest in native['output_sha256'].items():
            assert sha(root/path) == digest
        terminal = len(record['ofe_order']); width = D(str(record['emitted']['width_m']))
        lines = (capsule/'output/H1.pass.dat').read_text().splitlines()
        years, first = map(int,lines[2].split())
        volume = D(0); mass = D(0); events = 0; i = 6
        dates = set(); labels = {}
        while i < len(lines):
            label = lines[i][:8].strip(); parts = lines[i][8:].split(); i += 1
            size = {'EVENT':26,'SUBEVENT':8,'NO EVENT':4}[label]
            while len(parts) < size:
                parts += lines[i].split(); i += 1
            assert len(parts) == size
            year, julian = map(int,parts[:2]); date = datetime.date(year,1,1)+datetime.timedelta(days=julian-1)
            assert date.year == year and date not in dates
            dates.add(date); labels[date] = label
            if label == 'EVENT':
                v = D(parts[6]); concentrations = [D(x) for x in parts[14:19]]
                assert v >= 0 and all(x >= 0 for x in concentrations)
                volume += v; mass += v*sum(concentrations); events += 1
                trailer=lines[i].split(); i += 1
                assert trailer[0]=='SRC3' and tuple(map(int,trailer[1:3]))==(year,julian)
                assert (trailer[3],len(trailer)) in (('0',4),('1',31))
                assert all(D(t).is_finite() for t in trailer[4:])
        start=datetime.date(first,1,1);end=datetime.date(first+years,1,1)
        assert dates == {start+datetime.timedelta(days=i) for i in range((end-start).days)}
        particles = private('audit_particle_closure_v2'); particles.TERMINAL_OFE = terminal
        particle = particles.audit(capsule/'record.json')
        assert particle['passed'] and not particle['flags']
        elements=particles.read_elements((capsule/'output/H1.element.dat').read_text().splitlines()[2:], first, unavailable=[])
        boundaries = {i:D(0) for i in range(1,terminal+1)}
        for (ofe,day,month,year),fields in elements.items():
            assert ofe in boundaries
            value=D(fields[23]);assert value.is_finite() and value >= 0
            assert datetime.date(first+year-1,month,day) in dates
            boundaries[ofe] += value*width/D(years)
        summary=result['response']['summary']
        close=lambda a,b:math.isclose(float(a),b,rel_tol=1e-10,abs_tol=1e-10)
        assert close(volume/D(years),summary['runoff_volume_m3'])
        assert close(mass/D(years),summary['sediment_yield_kg'])
        for row in result['response']['role_boundary']:
            assert close(boundaries[row['ofe']],row['boundary_kg_yr'])
        assert terminal==result['diagnostics']['terminal_ofe']
        checks.append({'context':key[0],'arm':key[1],'events':events,'days':len(dates),
                       'runoff_m3_yr':str(volume/D(years)),'pass_sediment_kg_yr':str(mass/D(years)),
                       'boundary_kg_yr':{str(k):str(v) for k,v in boundaries.items()},
                       'strict_particle_pass':True,'output_hashes':native['output_sha256']})
    output={'passed':True,'profile_count':18,'declaration_sha256':sha(ROOT/'declaration-v5.json'),
            'results_sha256':sha(ROOT/'results.json'),'reader_sha256':sha(__file__),
            'method':'Raw PASS Decimal arithmetic; fixed-width ELEMENT readback and unchanged strict particle audit with actual terminal OFE. No native reruns.',
            'checks':checks}
    path=ART/'parameterization-overrides-independent-readback.json'
    with path.open('x') as stream:
        json.dump(output,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in output.items() if k!='checks'},indent=2))

if __name__ == '__main__':
    main()

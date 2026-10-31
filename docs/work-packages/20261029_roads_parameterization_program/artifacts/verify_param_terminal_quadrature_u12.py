"""Independent quadrature of retained model-error bounds; no source changes."""
from pathlib import Path
import hashlib,importlib.util,json
import mpmath as mp
mp.mp.dps=80
script=Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/audit_param_terminal_matrix_u12.py')
spec=importlib.util.spec_from_file_location('audit',script);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
audit_path=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/param-terminal-matrix-audit-u12/final-receipt.json')
rows=json.loads(audit_path.read_text())['negative_support']
rows=[r for r in rows if r.get('weighted_errors')]
rows=sorted(rows,key=lambda r:max(float(e['raw_vs_clipped_model_error']) for e in r['weighted_errors']),reverse=True)
selected=[];seen=set()
for row in rows:
 key=tuple(row[k] for k in ('a','b','c','phi','q','ktrato'))
 if key not in seen:seen.add(key);selected.append(row)
 if len(selected)==12:break
for a,b,c,phi in [(0,-1,1-2**-23,-1),(0,-1,1-2**-23,-2),(-2,1,1-2**-22,-1),(-2,1,1-2**-22,-2)]:
 selected.append(audit.classify(f'NC_DEP 1 1 1 0 1 0 1 {a:.9g} {b:.9g} {c:.9g} {phi} 0 0 -1 1 1 -1e-7'))
results=[]
for row in selected:
 A,B,K,E,phi=map(mp.mpf,(row['a'],row['b'],row['ktrato'],row['wet_end'],row['phi']))
 root=mp.mpf(row['root']);p=-phi;d0=E-root
 for item in row['weighted_errors']:
  delta=E-mp.mpf(item['coordinate']);limit=p*mp.log(d0/delta)
  # Start from integral of -Craw'(s), using the damping kernel and a log-distance coordinate.
  def integrand(w):
   distance=delta*mp.exp(w/p)
   position=E-distance
   return -K*(2*A*position+B)*mp.exp(-w)*distance/p
  knots=sorted(set([mp.mpf(0)]+[min(mp.mpf(v),limit) for v in (1,10,100)]+[limit]))
  direct=mp.quad(integrand,knots)
  closed=mp.mpf(item['raw_vs_clipped_model_error'])
  relative=abs(direct-closed)/abs(closed)
  assert relative<mp.mpf('1e-50'),(row,direct,closed,relative)
  results.append(dict(case=row.get('case','synthetic'),coordinate=item['coordinate'],relative_difference=str(relative),direct_quadrature=str(direct),closed_form=str(closed)))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=audit_path.parent/'quadrature-verification.json'
out.write_text(json.dumps(dict(audit_receipt_sha256=sha(audit_path),audit_script_sha256=sha(script),
                              verification_script_sha256=sha(Path(__file__)),
                              mpmath_version=mp.__version__,decimal_precision=80,
                              coordinate_count=len(results),results=results),indent=2)+'\n')
print('Verified',len(results),'native-coordinate bounds by independent 80-digit quadrature, including phi=-1 and -2 and concave hump inputs.')
print('Maximum relative difference',max(mp.mpf(r['relative_difference']) for r in results))

from pathlib import Path
import json, math
root=Path('/workdir/watershed-physical-water-repair-20261021')
data=json.loads((root/'mc-continuity-v3/receipt.json').read_text())
def storage(nodes, coeff):
 return sum(k*(x*i+(1-x)*o) for (k,x),i,o in zip(coeff,nodes,nodes[1:]))
result=[]
for case in data:
 if case['method']!=4: continue
 rows=[]
 for previous,current in zip(case['days'],case['days'][1:]):
  old=previous['final_nodes'];new=current['initial_nodes'];n0=len(old)-1;n1=len(new)-1
  k0,x0=previous['last_segment_coefficients'][0]
  assert all(pair==[k0,x0] for pair in previous['last_segment_coefficients'])
  mapped=[]
  for j in range(n1+1):
   x=j*n0/n1;k=min(int(x),n0-1);w=x-k
   mapped.append((1-w)*old[k]+w*old[k+1])
  # Counterfactual decomposition only: retain prior K per unit length and X.
  # This is an MC numerical diagnostic, not physical remapping authority.
  coeff=[[k0*n0/n1,x0]]*n1
  old_h=storage(old,previous['last_segment_coefficients'])
  grid_h=storage(mapped,coeff)
  mapped[0]=new[0]
  boundary_h=storage(mapped,coeff)
  native_h=storage(new,coeff)
  new_h=storage(new,current['first_segment_coefficients'])
  rows.append({'day':current['day'],'old_segments':n0,'new_segments':n1,
   'grid_interpolation_at_prior_K_per_length_m3':grid_h-old_h,
   'upstream_boundary_replacement_m3':boundary_h-grid_h,
   'native_remap_rounding_m3':native_h-boundary_h,
   'coefficient_revaluation_m3':new_h-native_h,
   'combined_jump_m3':new_h-old_h,
   'max_remap_rate_error_m3s':max(abs(a-b) for a,b in zip(mapped,new))})
 result.append({k:v for k,v in case.items() if k!='days'}|{'transitions':rows})
(root/'mc4-transition-decomposition.json').write_text(json.dumps(result,indent=2)+'\n')
for c in result:
 if c['mode']==1:print(c['fixed_grid'],c['placement'],c['transitions'])

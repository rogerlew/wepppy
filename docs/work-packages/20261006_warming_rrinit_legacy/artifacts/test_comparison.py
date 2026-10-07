"""Focused checks for comparison direction, zero denominators and input selector."""
import compare_builds as compare
import run_experiment as runner

runner.test()
r=compare.stats([0.,1.,2.],[0.,2.,1.])
assert r['changed']==2 and r['lower']==1 and r['higher']==1
assert r['min_percent']==-50 and r['max_percent']==100
assert r['sum_change_percent']==0 and r['positive_reference_n']==2
r=compare.stats([0.,0.],[0.,0.])
assert r['min_percent'] is None and r['sum_change_percent'] is None
r=compare.stats([2.,4.],[2.,4.])
assert r['changed']==0 and r['max_abs_difference']==0
print('All focused comparison and input-selector tests passed')

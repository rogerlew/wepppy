set pagination off
set confirm off
set debuginfod enabled off
set stop-on-solib-events 1
run --library-path /wc1/runs/ro/roads-parameterization-program-20261029/container-runtime /workdir/wepppy/wepp_runner/bin/wepp_261029 < p1.run > native.stdout 2> native.stderr
add-symbol-file /workdir/wepppy/wepp_runner/bin/wepp_261029 0x402300
set stop-on-solib-events 0
set language fortran
break watbal_hourly.for:348 if year .eq. 16 .and. sdate .eq. 54 .and. iplane .eq. 2
continue
disable 1
break watbal_hourly.for:511
continue
python
import json
r={}
for key in ('fin','returnrouted','returnbase','returnarea','ui_HUrunf','ui_Hcrunf','ui_LFtstp','wmelt(iplane)','rain(iplane)'):
    r[key]=float(gdb.parse_and_eval(key))
n=int(gdb.parse_and_eval('nsl(iplane)'))
r['stock']=[float(gdb.parse_and_eval(f'st({i},iplane)')) for i in range(1,n+1)]
r['frozen']=[float(gdb.parse_and_eval(f'frzw({i},iplane)')) for i in range(1,n+1)]
for key in ('ui_SUrunf','ui_LfUrf'):
    r[key]=[float(gdb.parse_and_eval(f'{key}({i})')) for i in range(1,int(r['ui_LFtstp'])+1)]
print('TRACE_JSON '+json.dumps(r))
end
disable 2
continue

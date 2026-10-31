set pagination off
set confirm off
set debuginfod enabled off
set stop-on-solib-events 1
run --library-path /wc1/runs/ro/roads-parameterization-program-20261029/container-runtime /workdir/wepppy/wepp_runner/bin/wepp_261029 < p1.run > native.stdout 2> native.stderr
add-symbol-file /workdir/wepppy/wepp_runner/bin/wepp_261029 0x402300
set stop-on-solib-events 0
set language fortran
break watbal_hourly.for:348 if year .eq. 7 .and. sdate .eq. 6 .and. iplane .eq. 2
continue
frame 2
python
for expr in ('year', 'sdate', 'iplane', 'iuprun(1:3)', 'wmelt(1:3)', 'slplen(1:3)', 'efflen(1:3)', 'ks(1:3)', 'aveks(1:3)', 'wmlvar', 'wmllen', 'p', 'runoff(1:3)', 'runtmp(1:3)', 'xmxint(iplane)', 'aveksm', 'jumpfg', 'jmpfg2'):
    try: print(expr,gdb.parse_and_eval(expr))
    except gdb.error as exc: print(str(exc))
end
disable 1
continue

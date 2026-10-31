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
disable 1
break watbal_hourly.for:511
continue
python
for expr in ('year', 'sdate', 'iplane', 'ii', 'fin', 'returnrouted', 'returnbase', 'returnarea', 'ui_HUrunf', 'ui_Hcrunf', 'st(1:nsl(iplane),iplane)', 'frzw(1:nsl(iplane),iplane)', 'ui_SUrunf(1:24)', 'ui_LfUrf(1:24)', 'wmelt(iplane)', 'rain(iplane)'):
    try: print(expr,gdb.parse_and_eval(expr))
    except gdb.error as exc: print(str(exc))
end
disable 2
continue

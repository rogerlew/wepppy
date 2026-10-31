"""Remaining raw-polynomial versus clipped-capacity interval question."""
exec(open('/tmp/route-u9-negative-capacity-probe.py').read().split('f=m.native_route')[0])
p=root/'tests/native/roads_route_boundary_driver.for'
s=p.read_text().replace('      cinftc(2)=-.001',
                       '      cinftc(2)=-.001\n      binftc(2)=.1',1)
p.write_text(s)
f=m.native_route.__wrapped__(Factory())
print('native',f(.1,initial=.01))
print('clipped-capacity reference at .01',.01*(.1/.11)**2)

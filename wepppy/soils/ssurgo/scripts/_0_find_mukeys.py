
fns = glob('/geodata/ssurgo/201703/rasters/*.tif')

mukeys = set()
for fn in fns:
    sm = SurgoMap(fn)
    mukeys.update([int(v) for v in sm.mukeys])
    
    print fn, len(mukeys)
   
with open('mukeys.txt', 'w') as fp:
    fp.write('\n'.join([str(v) for v in list(mukeys)]))
import os
from struct import *

from _1_build import load_mukeys

if __name__ == "__main__":
    mukeys = load_mukeys()
    mukeys = [int(v) for v in mukeys]
    mukeys = sorted(mukeys)
    
    fp_d = open('mukeys.dat', 'wb')
    fp_m = open('mukeys_mask.dat', 'wb')
    
    asint = []
    valid = []
    invalid = []
    unknown = []
    for m in mukeys:
        s = pack('i', int(m))
        fp_d.write(s)
        
        m = str(m)
        
        if _exists(_join('cache', m[:3], '%s.sol' % m)):
            valid.append(m)
            fp_m.write(pack('b', True))
            
        elif _exists(_join('invalid', m[:3], m)):
            invalid.append(m)
            fp_m.write(pack('b', False))
        else:
            unknown.append(m)
            fp_m.write(pack('b', False))
            
        asint.append(int(m))
            
    fp_d.close()
    fp_m.close()
    
    print 'valid\t', len(valid)
    print 'invalid\t', len(invalid)
    print 'unknown\t', len(unknown)
    print 'total\t', len(valid) + len(invalid) + len(unknown)
    print
    print 'min\t', min(asint)
    print 'min\t', max(asint)
    print mukeys[:10]

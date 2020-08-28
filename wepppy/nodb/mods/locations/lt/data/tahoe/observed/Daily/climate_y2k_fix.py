from os.path import split as _split
from os.path import join as _join
from glob import glob

cli_fns = glob('*.cli')

for fn in cli_fns:
    print(fn)
    lines = open(fn).readlines()
    for i in range(15,len(lines)):
        line = lines[i].split()
        year = int(line[2])
        year += 1900

        line[2] = str(year)
        lines[i] = '\t'.join(line)
        if i != len(lines) - 1:
            lines[i] += '\n'

    with open(_join('y2k_fixed', _split(fn)[1]), 'w') as fp:
        fp.write(''.join(lines))

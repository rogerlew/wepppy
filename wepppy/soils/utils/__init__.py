def modify_ksat(src_fn, dst_fn, ksat):
    with open(src_fn) as fp:
        lines = fp.readlines()

    while len(lines[-1].strip()) == 0:
        del lines[-1]

    lastline = lines[-1].split()
    lastline[-1] = '{}'.format(ksat)
    lines[-1] = ' '.join(lastline)

    with open(dst_fn, 'w') as fp:
        fp.writelines(lines)


if __name__ == "__main__":
    src_fn = '/Users/roger/wepppy/wepppy/soils/ssurgo/tests/2485028.sol'
    ksat = 0.04
    dst_fn = '/Users/roger/wepppy/wepppy/soils/ssurgo/tests/testsoils/2485028-{}.sol'.format(ksat)
    modify_ksat(src_fn, dst_fn, ksat)

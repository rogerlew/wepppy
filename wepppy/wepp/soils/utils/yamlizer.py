import oyaml as yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class YamlSoil(object):
    def __init__(self, fn):
        if fn.endswith('.sol'):
            self._parse_sol(fn)
        elif fn.endswith('.yaml'):
            self._load_yaml(fn)

    def _parse_sol(self, fn):
        print(fn)
        with open(fn) as fp:
            lines = fp.readlines()

        header = [L.replace('#', '').strip() for L in lines if L.startswith('#')]
        header = [L for L in header if L != '']
        lines = [L.strip() for L in lines if not L.startswith('#')]

        datver = lines[0]  # data version
        solcom = lines[1]  # user comment line

        line2 = lines[2].split()
        ntemp = int(line2[0])   # number of ofes
        ksflag = int(line2[1])  # use internal hydraulic conductivity adjustments

        ofes = []
        i = 3
        for ofe_counter in range(ntemp):
            line = lines[i].split('\t')
            slid, texid, nsl, salb, sat, ki, kr, shcrit, avke = line

            nsl = int(nsl)

            i += 1
            horizons = []
            for j in range(nsl):
                line = lines[i].split()
                solthk, sand, clay, orgmat, cec, rfg = line
                horizons.append(
                    dict(solthk=float(solthk), sand=float(sand), clay=float(clay),
                         orgmat=float(orgmat), cec=float(cec), rfg=float(rfg)))

                i += 1

            ofes.append(
                dict(slid=slid.replace("'", '').replace('"', ''),
                     texid=texid.replace("'", '').replace('"', ''),
                     nsl=int(nsl),
                     salb=float(salb),
                     sat=float(sat),
                     ki=float(ki),
                     kr=float(kr),
                     shcrit=float(shcrit),
                     avke=float(avke),
                     horizons=horizons))

        try:
            res_lyr = lines[i].split()

            if len(res_lyr) == 4:
                res_lyr = [res_lyr[0], res_lyr[2], res_lyr[3]]
            res_lyr = [int(res_lyr[0]), float(res_lyr[1]), float(res_lyr[2])]
        except:
            res_lyr = None

        soil = dict(header=header,
                    datver=datver,
                    solcom=solcom,
                    ntemp=ntemp,
                    ksflag=ksflag,
                    ofes=ofes,
                    res_lyr=res_lyr)

        yaml_txt = yaml.dump(soil)

        self.obj = yaml.safe_load(yaml_txt)
        print(self.obj)

    def _load_yaml(self, fn):
        with open(fn) as fp:
            yaml_txt = fp.read()
            self.obj = yaml.safe_load(yaml_txt)

    def dump_yaml(self, dst):
        with open(dst, 'w') as fp:
            fp.write(yaml.dump(self.obj))


if __name__ == "__main__":
    from glob import glob
    import csv

    #YamlSoil('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/High sev fire-loam.sol')

    sol_fns = glob('/home/roger/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/*.sol')
    #sol_fns = glob('/home/roger/PycharmProjects/wepppy/wepppy/nodb/mods/baer/data/soils/*.sol')

    #fp = open('/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/baer/data/soils/summary.csv', 'w')
    fp = open('/home/roger/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/summary.csv', 'w')
    fp.write('slid,texid,burnclass,salb,sat,ki,kr,shcrit,avke,sand,clay,orgmat,cec,rfg,solthk\n')
    for sol_fn in sol_fns:
        print(sol_fn)
        sol = YamlSoil(sol_fn)
        sol.dump_yaml(sol_fn.replace('.sol', '.sol.yaml'))

        ofe = sol.obj['ofes'][0]
        hor = ofe['horizons'][0]

        burnclass = ''
        if 'high' in ofe['slid'].lower():
            burnclass = 'high'

        if 'low' in ofe['slid'].lower():
            burnclass = 'low'

        fp.write('{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'
                 .format(ofe['slid'], ofe['texid'], burnclass, ofe['salb'], ofe['sat'], ofe['ki'], ofe['kr'], ofe['shcrit'], ofe['avke'],
                         hor['sand'], hor['clay'], hor['orgmat'], hor['cec'], hor['rfg'], hor['solthk']))

    fp.close()
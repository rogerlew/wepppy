import csv

if __name__ == "__main__":
    fn = '/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/lt/data/lt_cover_defaults.csv'
    with open(fn) as fp:
        d = {}
        rdr = csv.DictReader(fp)
        for row in rdr:
            d[row['key']] = row

    print(d)
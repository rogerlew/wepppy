import csv


def hill_report_csv(hill_rpt, fn):
    fp = open(fn, 'w')

    wtr = csv.writer(fp)

    wtr.writerow(hill_rpt.hdr)
    wtr.writerow(hill_rpt.units)

    for row in hill_rpt:
        wtr.writerow([value for value, units in row])

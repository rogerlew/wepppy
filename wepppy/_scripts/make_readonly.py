import csv
from os.path import exists


if __name__ == "__main__":
    with open('BullRun_Runs_ID.csv') as fp:
        rdr = csv.DictReader(fp)
        for row in rdr:
            run_id = row['RunID']
            if exists(f'/geodata/weppcloud_runs/{run_id}'):
                if not exists(f'/geodata/weppcloud_runs/{run_id}/READONLY'):
                    print(row)
                    with open(f'/geodata/weppcloud_runs/{run_id}/READONLY', 'w') as pf:
                        pass

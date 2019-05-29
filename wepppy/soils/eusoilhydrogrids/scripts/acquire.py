from urllib.request import urlopen

if __name__ == '__main__':
    datasets = ['THS', 'KS', 'WP', 'FC']
    depths = ['sl1', 'sl2', 'sl3', 'sl4', 'sl5', 'sl6', 'sl7']
    url_template = 'https://eusoilhydrogrids.rissac.hu/dl1k.php?nev=Roger+Lew&email=rogerlew%40uidaho.edu&dataset={dataset}&depth={depth}'

    for dataset in datasets:
        for depth in depths:

            url = url_template.format(dataset=dataset, depth=depth)
            fname = '{dataset}_{depth}.zip'.format(dataset=dataset, depth=depth)

            print(url)
            output = urlopen(url)
            with open(fname, 'wb') as fp:
                fp.write(output.read())

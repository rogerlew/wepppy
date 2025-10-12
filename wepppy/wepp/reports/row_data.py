def parse_name(colname):
    units = parse_units(colname)
    if units is None:
        return colname

    return colname.replace('({})'.format(units), '').strip()


def parse_units(colname):
    try:
        colsplit = colname.strip().split()
        if len(colsplit) < 2:
            return None

        if '(' in colsplit[-1]:
            return colsplit[-1].replace('(', '').replace(')', '')

        return None
    except IndexError:
        return None


class RowData:
    def __init__(self, row):

        self.row = row

    def __getitem__(self, item):
        for colname in self.row:
            if colname.startswith(item):
                return self.row[colname]

        raise KeyError

    def __iter__(self):
        for colname in self.row:
            value = self.row[colname]
            units = parse_units(colname)
            yield value, units
from wepppy.all_your_base import parse_name, parse_units

class ReportBase(object):
    @property
    def hdr(self):
        for colname in self.header:
            yield parse_name(colname)

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

if __name__ == "__main__":
    pass
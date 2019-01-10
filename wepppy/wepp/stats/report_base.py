# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import csv

from wepppy.all_your_base import parse_name, parse_units


class ReportBase(object):
    header = []

    @property
    def hdr(self):
        for colname in self.header:
            yield parse_name(colname)

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

    def write(self, fp, write_header=True, run_descriptors=None):

        wtr = csv.writer(fp)

        if write_header:
            hdr = []

            for cname, units in zip(self.hdr, self.units):
                hdr.append(cname)
                if units is not None:
                    hdr[-1] += ' (%s)' % units

            if run_descriptors is not None:
                hdr = [cname for cname, desc in run_descriptors] + hdr

            wtr.writerow(hdr)

        for row in self:
            data = [value for value, units in row]
            if run_descriptors is not None:
                data = [desc for cname, desc in run_descriptors] + data
            wtr.writerow(data)

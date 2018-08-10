# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

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

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import exists as _exists

import warnings
from datetime import datetime

from wepppy.all_your_base import (
    parse_datetime
)


class LogMixin(object):

    #
    # Log methods
    #
    def _calc_log_elapsed(self):
        try:
            with open(self.status_log) as fp:
                lines = fp.readlines()
                r0 = parse_datetime(lines[0])
                t0 = parse_datetime(lines[-1])

            r_elapsed = datetime.now() - r0
            t_elapsed = datetime.now() - t0

            return r_elapsed, t_elapsed, lines[-1]
        except FileNotFoundError:
            return None, None, None

    def _write(self, msg):
        if _exists(self.status_log):
            with open(self.status_log, 'a') as fp:
                fp.write(msg)
        else:
            try:
                with open(self.status_log, 'w') as fp:
                    fp.write(msg)
            except FileNotFoundError:
                warnings.warn('FileNotFoundError')

    def get_log_last(self):
        r_elapsed, t_elapsed, s = self._calc_log_elapsed()

        if s is None:
            return ''
        if s.strip().endswith('...'):
            return '{} ({:.2f}s | {:.2f}s)'.format(s, t_elapsed.total_seconds(), r_elapsed.total_seconds())
        else:
            return s

    def log(self, msg):
        t0 = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')

        try:
            self._write('[{}] {}'.format(t0, msg))
        except FileNotFoundError:
            warnings.warn('FileNotFoundError')

    def log_done(self):
        r_elapsed, t_elapsed, s = self._calc_log_elapsed()

        if s is None:
            warnings.warn('FileNotFoundError')
            return

        self._write('done. ({:.2f}s | {:.2f}s)\n'.format(t_elapsed.total_seconds(), r_elapsed.total_seconds()))

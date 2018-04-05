# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard libraries

import os
from os.path import join as _join

from collections import OrderedDict

# non-standard
import jsonpickle

# weppy submodules
from .base import NoDbBase

converters = {
    'temperature': {
        ('degf', 'degc'): lambda v: (v - 32.0) / 1.8,
        ('degc', 'degf'): lambda v: v * 1.8 + 32
    },
    'distance': {
        ('km', 'mi'): lambda v: v * 0.621371,
        ('mi', 'm'): lambda v: v * 1.60934
    },
    'sm-distance': {
        ('m', 'ft'): lambda v: v * 3.28084,
        ('ft', 'm'): lambda v: v * 0.3048
    },
    'xs-distance': {
        ('mm', 'in'): lambda v: v * 0.0393701,
        ('in', 'mm'): lambda v: v * 25.4
    },
    'area': {
        ('ha', 'acre'): lambda v: v * 2.47105,
        ('ha', 'm^2'): lambda v: v * 1000.0,
        ('m^2', 'ha'): lambda v: v * 0.0001,
        ('m^2', 'acre'): lambda v: v * 0.000247105,
        ('acre', 'ha'): lambda v: v * 0.404686,
        ('acre', 'm^2'): lambda v: v * 4046.86266972
    },
    'weight': {
        ('tonne', 'ton'): lambda v: v * 1.10231,
        ('ton', 'tonne'): lambda v: v * 25.4
    },
    'weight-annual': {
        ('tonne/yr', 'ton/yr'): lambda v: v * 1.10231,
        ('ton/yr', 'tonne/yr'): lambda v: v * 25.4
    },
    'sm-weight': {
        ('kg', 'lb'): lambda v: v * 2.20462,
        ('lb', 'kg'): lambda v: v * 0.453592
    },
    'sm-weight-annual': {
        ('kg/yr', 'lb/yr'): lambda v: v * 2.20462,
        ('lb/yr', 'kg/yr'): lambda v: v * 0.453592
    },
    'volume': {
        ('m^3', 'ft^3'): lambda v: v * 35.3146667,
        ('ft^3', 'm^3'): lambda v: v * 0.0283168
    },
    'volume-annual': {
        ('m^3/yr', 'ft^3/yr'): lambda v: v * 35.3146667,
        ('ft^3/yr', 'm^3/yr'): lambda v: v * 0.0283168
    },
    'flow': {
        ('m^3/s', 'ft^3/min'): lambda v: v * 2118.88,
        ('m^3/s', 'ft^3/s'): lambda v: v * 35.3147,
        ('ft^3/min', 'm^3/s'): lambda v: v * 0.000471947,
        ('ft^3/min', 'ft^3/s'): lambda v: v * 0.0166667,
        ('ft^3/s', 'm^3/s'): lambda v: v * 0.0283168,
        ('ft^3/s', 'ft^3/min'): lambda v: v * 60.0
    },
    'sm-surface-density': {
        ('kg/ha', 'lb/acre'): lambda v: v * 0.892179,
        ('kg/ha', 'kg/m^2'): lambda v: v * 0.0001,
        ('lb/acre', 'kg/ha'): lambda v: v * 1.12085,
        ('lb/acre', 'kg/m^2'): lambda v: v * 0.000112085116,
        ('kg/m^2', 'kg/ha'): lambda v: v * 10000.0,
        ('kg/m^2', 'lb/acre'): lambda v: v * 8921.79
    },
    'sm-surface-density-annual': {
        ('kg/ha/yr', 'lb/acre/yr'): lambda v: v * 0.892179,
        ('kg/ha/yr', 'kg/m^2/yr'): lambda v: v * 0.0001,
        ('lb/acre/yr', 'kg/ha/yr'): lambda v: v * 1.12085,
        ('lb/acre/yr', 'kg/m^2/yr'): lambda v: v * 0.000112085116,
        ('kg/m^2/yr', 'kg/ha/yr'): lambda v: v * 10000.0,
        ('kg/m^2/yr', 'lb/acre/yr'): lambda v: v * 8921.79
    },
    'surface-density': {
        ('tonne/ha', 'ton/acre'): lambda v: v * 0.44609,
        ('ton/acre', 'tonne/ha'): lambda v: v * 2.24170010536
    },
    'surface-density-annual': {
        ('tonne/ha/yr', 'ton/acre/yr'): lambda v: v * 0.44609,
        ('ton/acre/yr', 'tonne/ha/yr'): lambda v: v * 2.24170010536
    }
}

precisions = OrderedDict([
    ('temperature', OrderedDict([
        ('degc', 1),
        ('degf', 1)])
     ),
    ('distance', OrderedDict([
        ('km', 2),
        ('mi', 2)])
     ),
    ('sm-distance', OrderedDict([
        ('m', 1),
        ('ft', 1)])
     ),
    ('xs-distance', OrderedDict([
        ('mm', 1),
        ('in', 2)])
     ),
    ('area', OrderedDict([
        ('ha', 3),
        ('acre', 3),
        ('m^2', 0)])
     ),
    ('weight', OrderedDict([
        ('tonne', 3),
        ('ton', 3)])
     ),
    ('weight-annual', OrderedDict([
        ('tonne/yr', 3),
        ('ton/yr', 3)])
     ),
    ('sm-weight', OrderedDict([
        ('kg', 1),
        ('lb', 0)])
     ),
    ('sm-weight-annual', OrderedDict([
        ('kg/yr', 3),
        ('lb/yr', 3)])
     ),
    ('volume', OrderedDict([
        ('m^3', 0),
        ('ft^3', 0)])
     ),
    ('volume-annual', OrderedDict([
        ('m^3/yr', 0),
        ('ft^3/yr', 0)])
     ),
    ('flow', OrderedDict([
        ('m^3/s', 2),
        ('ft^3/min', 0),
        ('ft^3/s', 2)])
     ),
    ('sm-surface-density', OrderedDict([
        ('kg/ha', 3),
        ('lb/acre', 3),
        ('kg/m^2', 1)])
     ),
    ('sm-surface-density-annual', OrderedDict([
        ('kg/ha/yr', 3),
        ('lb/acre/yr', 3),
        ('kg/m^2/yr', 3)])
     ),
    ('surface-density', OrderedDict([
        ('tonne/ha', 1),
        ('ton/acre', 1)])
     ),
    ('surface-density-annual', OrderedDict([
        ('tonne/ha/yr', 2),
        ('ton/acre/yr', 2)])
     )
])

for _k in converters:
    assert _k in precisions

for _k in precisions:
    assert _k in converters


class UnitizerNoDbLockedException(Exception):
    pass


class Unitizer(NoDbBase):
    __name__ = 'Unitizer'

    def __init__(self, wd, cfg_fn):
        super(Unitizer, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:

            # make the first in the list the default
            self._preferences = \
                {k: list(v.keys())[0] for k, v in precisions.items()}

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def preferences(self):
        return self._preferences

    def set_preferences(self, kwds):

        # noinspection PyBroadException
        try:
            self.lock()

            for k, v in kwds.items():
                assert k in precisions
                assert v in precisions[k]
                self._preferences[k] = v

            self.dump_and_unlock()

            return self._preferences

        except Exception:
            self.unlock('-f')
            raise

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'unitizer.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Unitizer), db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'unitizer.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'unitizer.nodb.lock')

    @staticmethod
    def context_processor_package():
        global converters, precisions

        def tostring(v, p):
            if p == 0:
                return str(int(v))

            fmt = '%.{}f'.format(int(p))
            try:
                return fmt % float(v)
            except:
                return str(v)

        def determine_unitclass(in_units):
            for k, v in precisions.items():
                if in_units in v.keys():
                    return k

            return None

        def str_other_class(other_classes):
            oc = ''
            if other_classes is not None:
                oc = ' ' + ' '.join(other_classes)

            return oc

        def cls_units(units):
            return str(units).replace('/', '_') \
                .replace('^2', '-sqr') \
                .replace('^3', '-cube')

        def str_units(units):
            return str(units).replace('^2', '<sup>2</sup>') \
                .replace('^3', '<sup>3</sup>')

        def unitizer_units(in_units, other_classes=None):

            if in_units is None:
                return ''

            unitclass = determine_unitclass(in_units)
            if unitclass is None:
                return str(in_units)

            oc = str_other_class(other_classes)

            s = '<div class="unitizer units-{u0} {oc}">{u1}</div>' \
                .format(u0=cls_units(in_units), u1=str_units(in_units), oc=oc)

            for u in precisions[unitclass].keys():
                if u == in_units:
                    continue
                s += '<div class="unitizer units-{u0} invisible{oc}">{u1}</div>' \
                    .format(u0=cls_units(u), u1=str_units(u), oc=oc)

            return '<div class="unitizer-wrapper">{}</div>'.format(s)

        def unitizer(value, in_units, other_classes=None):

            if in_units is None:
                return str(value)

            unitclass = determine_unitclass(in_units)
            if unitclass is None:
                return '<i>{}</i>'.format(value)

            oc = str_other_class(other_classes)

            p = precisions[unitclass][in_units]
            s = '<div class="unitizer units-{u} {oc}">{v}</div>' \
                .format(u=cls_units(in_units), oc=oc, v=tostring(value, p))

            for u in precisions[unitclass].keys():
                if u == in_units:
                    continue
                f = converters[unitclass][(in_units, u)]
                p = precisions[unitclass][u]
                try:
                    v = tostring(f(value), p)
                except:
                    v = '<i>%s</i>' % str(value)

                s += '<div class="unitizer units-{u} invisible{oc}">{v}</div>' \
                    .format(u=cls_units(u), oc=oc, v=v)

            return '<div class="unitizer-wrapper">{}</div>'.format(s)

        return dict(cls_units=cls_units,
                    str_units=str_units,
                    unitizer=unitizer,
                    unitizer_units=unitizer_units)

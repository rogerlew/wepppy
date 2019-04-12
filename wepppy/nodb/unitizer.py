# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard libraries

import os
from os.path import join as _join
from os.path import exists as _exists

from collections import OrderedDict

# non-standard
import jsonpickle

# weppy submodules
from .base import NoDbBase

from wepppy.all_your_base import isfloat

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
    'xs-distance-rate': {
        ('mm/hour', 'in/hour'): lambda v: v * 0.0393701,
        ('in/hour', 'mm/hour'): lambda v: v * 25.4
    },
    'xs-annual': {
        ('mm/yr', 'in/yr'): lambda v: v * 0.0393701,
        ('in/yr', 'mm/yr'): lambda v: v * 25.4
    },
    'area': {
        ('ha', 'acre'): lambda v: v * 2.47105,
        ('ha', 'm^2'): lambda v: v * 1000.0,
        ('ha', 'km^2'): lambda v: v * 0.01,
        ('m^2', 'ha'): lambda v: v * 0.0001,
        ('m^2', 'acre'): lambda v: v * 0.000247105,
        ('m^2', 'km^2'): lambda v: v * 0.000001,
        ('acre', 'ha'): lambda v: v * 0.404686,
        ('acre', 'm^2'): lambda v: v * 4046.86266972,
        ('acre', 'km^2'): lambda v: v * 0.00404686,
        ('km^2', 'ha'): lambda v: v * 100.0,
        ('km^2', 'm^2'): lambda v: v * 1000000.0,
        ('km^2', 'acre'): lambda v: v * 247.105,
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
        ('ft^3', 'm^3'): lambda v: v * 0.0283168,
        ('m^3', 'yd^3'): lambda v: v * 1.30795,
        ('ft^3', 'yd^3'): lambda v: v * 0.037037,
        ('yd^3', 'm^3'): lambda v: v * 0.764555,
        ('yd^3', 'ft^3'): lambda v: v * 27.0
    },
    'volume-annual': {
        ('m^3/yr', 'ft^3/yr'): lambda v: v * 35.3146667,
        ('ft^3/yr', 'm^3/yr'): lambda v: v * 0.0283168,
        ('m^3/yr', 'yd^3/yr'): lambda v: v * 1.30795,
        ('ft^3/yr', 'yd^3/yr'): lambda v: v * 0.037037,
        ('yd^3/yr', 'm^3/yr'): lambda v: v * 0.764555,
        ('yd^3/yr', 'ft^3/yr'): lambda v: v * 27.0
    },
    'flow': {
        ('m^3/s', 'ft^3/min'): lambda v: v * 2118.88,
        ('m^3/s', 'ft^3/s'): lambda v: v * 35.3147,
        ('ft^3/s', 'm^3/s'): lambda v: v * 0.0283168
    },
    'xs-surface-density': {
        ('kg/ha,3', 'lb/acre,3'): lambda v: v * 0.892179,
        ('lb/acre,3', 'kg/ha,3'): lambda v: v * 1.12085,
    },
    'sm-surface-density': {
        ('kg/ha', 'lb/acre'): lambda v: v * 0.892179,
        ('kg/ha', 'kg/m^2'): lambda v: v * 0.0001,
        ('kg/ha', 'lb/mi^2'): lambda v: v * 570.994638,
        ('lb/acre', 'kg/ha'): lambda v: v * 1.12085,
        ('lb/acre', 'kg/m^2'): lambda v: v * 0.000112085116,
        ('lb/acre', 'lb/mi^2'): lambda v: v * 640,
        ('kg/m^2', 'kg/ha'): lambda v: v * 10000.0,
        ('kg/m^2', 'lb/acre'): lambda v: v * 8921.79,
        ('kg/m^2', 'lb/mi^2'): lambda v: v * 5709946.38,
        ('lb/mi^2', 'kg/ha'): lambda v: v * 0.00175132993,
        ('lb/mi^2', 'lb/acre'): lambda v: v * 0.0015625,
        ('lb/mi^2', 'kg/m^2'): lambda v: v * 1.75132993E-7,
    },
    'xs-surface-density-annual': {
        ('kg/ha/yr,3', 'lb/acre/yr,3'): lambda v: v * 0.892179,
        ('lb/acre/yr,3', 'kg/ha/yr,3'): lambda v: v * 1.12085,
    },
    'sm-surface-density-annual': {
        ('kg/ha/yr', 'lb/acre/yr'): lambda v: v * 0.892179,
        ('kg/ha/yr', 'kg/m^2/yr'): lambda v: v * 0.0001,
        ('kg/ha/yr', 'lb/mi^2/yr'): lambda v: v * 570.994638,
        ('lb/acre/yr', 'kg/ha/yr'): lambda v: v * 1.12085,
        ('lb/acre/yr', 'kg/m^2/yr'): lambda v: v * 0.000112085116,
        ('lb/acre/yr', 'lb/mi^2/yr'): lambda v: v * 640,
        ('kg/m^2/yr', 'kg/ha/yr'): lambda v: v * 10000.0,
        ('kg/m^2/yr', 'lb/acre/yr'): lambda v: v * 8921.79,
        ('kg/m^2/yr', 'lb/mi^2/yr'): lambda v: v * 5709946.38,
        ('lb/mi^2/yr', 'kg/ha/yr'): lambda v: v * 0.00175132993,
        ('lb/mi^2/yr', 'lb/acre/yr'): lambda v: v * 0.0015625,
        ('lb/mi^2/yr', 'kg/m^2/yr'): lambda v: v * 1.75132993E-7,
    },
    'surface-density': {
        ('tonne/ha', 'ton/acre'): lambda v: v * 0.44609,
        ('tonne/ha', 'ton/mi^2'): lambda v: v * 285.497319,
        ('ton/acre', 'tonne/ha'): lambda v: v * 2.24170010536,
        ('ton/acre', 'ton/mi^2'): lambda v: v * 640,
        ('ton/mi^2', 'tonne/ha'): lambda v: v * 0.00350265986,
        ('ton/mi^2', 'ton/acre'): lambda v: v * 0.0015625,
    },
    'surface-density-annual': {
        ('tonne/ha/yr', 'ton/acre/yr'): lambda v: v * 0.44609,
        ('tonne/ha/yr', 'ton/mi^2/yr'): lambda v: v * 285.497319,
        ('ton/acre/yr', 'tonne/ha/yr'): lambda v: v * 2.24170010536,
        ('ton/acre/yr', 'ton/mi^2/yr'): lambda v: v * 640,
        ('ton/mi^2/yr', 'tonne/ha/yr'): lambda v: v * 0.00350265986,
        ('ton/mi^2/yr', 'ton/acre/yr'): lambda v: v * 0.0015625,
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
    ('xs-distance-rate', OrderedDict([
        ('mm/hour', 1),
        ('in/hour', 2)])
     ),
    ('xs-annual', OrderedDict([
        ('mm/yr', 1),
        ('in/yr', 2)])
     ),
    ('area', OrderedDict([
        ('ha', 1),
        ('acre', 1),
        ('m^2', 0),
        ('km^2', 3)])
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
        ('yd^3', 0),
        ('ft^3', 0)])
     ),
    ('volume-annual', OrderedDict([
        ('m^3/yr', 0),
        ('yd^3/yr', 0),
        ('ft^3/yr', 0)])
     ),
    ('flow', OrderedDict([
        ('m^3/s', 2),
        ('ft^3/s', 2)])
     ),
    ('xs-surface-density', OrderedDict([
        ('kg/ha,3', 3),
        ('lb/acre,3', 3)])
     ),
    ('sm-surface-density', OrderedDict([
        ('kg/ha', 0),
        ('lb/acre', 0),
        ('kg/m^2', 1),
        ('lb/mi^2', 1)])
     ),
    ('xs-surface-density-annual', OrderedDict([
        ('kg/ha/yr,3', 3),
        ('lb/acre/yr,3', 3)])
     ),
    ('sm-surface-density-annual', OrderedDict([
        ('kg/ha/yr', 0),
        ('lb/acre/yr', 0),
        ('kg/m^2/yr', 3),
        ('lb/mi^2/yr', 3)])
     ),
    ('surface-density', OrderedDict([
        ('tonne/ha', 1),
        ('ton/acre', 1),
        ('ton/mi^2', 1)])
     ),
    ('surface-density-annual', OrderedDict([
        ('tonne/ha/yr', 2),
        ('ton/acre/yr', 2),
        ('ton/mi^2/yr', 2)])
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

            # make the second in the list the default (English Units)
            self._preferences = \
                {k: list(v.keys())[1] for k, v in precisions.items()}

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

            if _exists(_join(wd, 'READONLY')):
                return db

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
                .replace('^3', '-cube') \
                .replace(',', '-_')

        def str_units(units):
            return str(units)\
                .split(',')[0] \
                .replace('^2', '<sup>2</sup>') \
                .replace('^3', '<sup>3</sup>')

        def unitizer_units(in_units, other_classes=None, parentheses=False):

            if in_units is None:
                return ''

            if in_units == 'pct' or in_units == '%':
                return '%'

            unitclass = determine_unitclass(in_units)
            if unitclass is None:
                return str(in_units)

            oc = str_other_class(other_classes)

            if parentheses:
                s = '<div class="unitizer units-{u0} {oc}">({u1})</div>' \
                    .format(u0=cls_units(in_units), u1=str_units(in_units), oc=oc)
            else:
                s = '<div class="unitizer units-{u0} {oc}">{u1}</div>' \
                    .format(u0=cls_units(in_units), u1=str_units(in_units), oc=oc)

            for u in precisions[unitclass].keys():
                if u == in_units:
                    continue

                if parentheses:
                    s += '<div class="unitizer units-{u0} invisible{oc}">({u1})</div>' \
                        .format(u0=cls_units(u), u1=str_units(u), oc=oc)
                else:
                    s += '<div class="unitizer units-{u0} invisible{oc}">{u1}</div>' \
                        .format(u0=cls_units(u), u1=str_units(u), oc=oc)

            return '<div class="unitizer-wrapper">{}</div>'.format(s)

        def unitizer(value, in_units, other_classes=None, parentheses=False, precision=None):

            if value is None:
                return ''

            if precision is not None:
                assert float(int(precision)) == float(precision)
                precision = int(precision)

            if in_units is None:
                if precision is None:
                    precision = 3
                    try:
                        if float(int(value)) == float(value):
                            precision = 0
                    except:
                        pass

                if isfloat(value):
                    fmt = '%0.' + str(precision) + 'f'
                    return fmt % float(value)

                return str(value)

            if in_units == 'pct' or in_units == '%':
                try:
                    return '%0.2f' % float(value)
                except ValueError:
                    return '<i>{}</i>'.format(value)

            unitclass = determine_unitclass(in_units)
            if unitclass is None:
                return '<i>{}</i>'.format(value)

            oc = str_other_class(other_classes)

            if precision is not None:
                p = precision
            else:
                p = precisions[unitclass][in_units]

            if parentheses:
                s = '<div class="unitizer units-{u} {oc}">({v})</div>' \
                    .format(u=cls_units(in_units), oc=oc, v=tostring(value, p))
            else:
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

                if parentheses:
                    s += '<div class="unitizer units-{u} invisible{oc}">({v})</div>' \
                        .format(u=cls_units(u), oc=oc, v=v)
                else:
                    s += '<div class="unitizer units-{u} invisible{oc}">{v}</div>' \
                        .format(u=cls_units(u), oc=oc, v=v)

            return '<div class="unitizer-wrapper">{}</div>'.format(s)

        return dict(cls_units=cls_units,
                    str_units=str_units,
                    unitizer=unitizer,
                    unitizer_units=unitizer_units)

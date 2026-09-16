"""Bounded read-only evaluation of one accepted Staley predictor snapshot."""
from dataclasses import asdict
import math

from .staley2017 import probability, rainfall_threshold, _response

__all__ = ['response_curve', 'rainfall_provenance']


def rainfall_provenance(identity, frequency_source):
    mode = identity.get('climate_mode')
    modeled = mode in ('GridMetPRISM', 'Vanilla', 'PRISM', 'Future', 'CLIGEN', 'Cligen')
    return dict(design_origin='NOAA Atlas 14 statistical design rainfall' if frequency_source=='noaa'
                else 'Project climate statistical design rainfall',
                event_origin='Project climate events',climate_mode=mode,
                date_semantics=identity.get('date_semantics'),
                subdaily_origin='modeled_disaggregated' if modeled else 'not_recorded')


def response_curve(manifest, design_rows, duration):
    if type(duration) is not int or duration not in (15,30,60):
        raise ValueError('Unsupported rainfall window')
    markers = [dict(row) for row in design_rows if row['duration_minutes']==duration]
    if len(markers)>4:
        raise ValueError('Response curve design marker limit exceeded')
    result = dict(status='unavailable',reason='missing_predictors',duration_minutes=duration,
                  direction=None,intensity_units='mm/hour',probability_units='fraction',
                  range_max=None,points=[],p50=None,design_markers=markers)
    predictors = {key:manifest['predictor_snapshot']['predictors'][key]['value'] for key in ('T','F','S')}
    if any(value is None for value in predictors.values()):
        return result
    model = manifest['model']
    try:
        _,response,_ = _response(model,duration,**predictors)
        result['direction'] = 'increasing' if response>0 else 'decreasing' if response<0 else 'constant'
        p50 = rainfall_threshold(model,duration,**predictors,target_probability=.5)
        p99 = rainfall_threshold(model,duration,**predictors,target_probability=.99)
        result['p50'] = asdict(p50)
        arithmetic = next((v.reason for v in (p50,p99) if v.reason in ('arithmetic_overflow','arithmetic_underflow')),None)
        if arithmetic:
            result['reason']=arithmetic
            return result
        intensities = [r['intensity_mm_per_hour'] for r in markers
                       if r['intensity_mm_per_hour'] is not None and math.isfinite(r['intensity_mm_per_hour'])]
        if p50.status=='available':
            intensities.append(p50.intensity_mm_per_hour)
        maximum = max([1.,*intensities,*([p99.intensity_mm_per_hour] if p99.status=='available' else [])])
        samples = sorted(set([maximum*(i/100) for i in range(101)]+intensities))
        points = []
        for intensity in samples:
            rainfall = intensity*(duration/60)
            value = probability(model,duration,**predictors,rainfall_mm=rainfall)
            points.append(dict(duration_minutes=duration,intensity_mm_per_hour=intensity,
                               rainfall_mm=rainfall,probability=value))
        result.update(status='available',reason=None,range_max=maximum,points=points)
    except ArithmeticError:
        # Numerical boundary: keep valid saved tables, never clamp a failed curve.
        result.update(reason='arithmetic_overflow',points=[],range_max=None)
    return result

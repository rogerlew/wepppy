"""Print reproducible synthetic numerical evidence; never read project inputs.

Run with wctl run-python from the WEPPpy root and redirect stdout to
artifacts/synthetic_examples.json. Decimal is an independent arithmetic oracle.
"""

from dataclasses import asdict
from decimal import Decimal, localcontext
import json

from wepppy.nodb.mods.postfire_debris_flow.staley2017 import (
    probability, rainfall_threshold,
)


# Table 4 transcription independent of the library's coefficient dictionary.
ROWS = [
    ("M1", 15, "-3.63", ".41", ".67", ".70"),
    ("M1", 30, "-3.61", ".26", ".39", ".50"),
    ("M1", 60, "-3.21", ".17", ".20", ".220"),
    ("M3", 15, "-3.71", ".32", ".33", ".47"),
    ("M3", 30, "-3.79", ".21", ".19", ".36"),
    ("M3", 60, "-3.46", ".14", ".10", ".18"),
]


def main():
    cases = []
    predictors = dict(T=.4, F=.6, S=.3)
    for model, duration, b, ct, cf, cs in ROWS:
        with localcontext() as context:
            context.prec = 60
            q = Decimal(ct)*Decimal('.4') + Decimal(cf)*Decimal('.6') + Decimal(cs)*Decimal('.3')
            x = Decimal(b) + Decimal(8)*q
            expected_p = Decimal(1)/(Decimal(1) + (-x).exp())
            expected_r = -Decimal(b)/q
        p = probability(model, duration, **predictors, rainfall_mm=8)
        threshold = rainfall_threshold(model, duration, **predictors, target_probability=.5)
        reconstructed = probability(model, duration, **predictors, rainfall_mm=threshold.rainfall_mm)
        assert abs(p - float(expected_p)) < 1e-15
        assert abs(reconstructed - .5) < 1e-15
        cases.append(dict(
            model=model, duration_minutes=duration, predictors=predictors,
            rainfall_mm=8, rainfall_intensity_mm_per_hour=8*60/duration,
            q_decimal=str(q), x_decimal=str(x), probability=p,
            independent_probability_decimal=str(expected_p), target_probability=.5,
            threshold=asdict(threshold), independent_threshold_mm_decimal=str(expected_r),
            reconstructed_probability=reconstructed,
        ))
    edge_cases = []
    baseline = probability('M1', 15, T=0, F=0, S=0, rainfall_mm=0)
    for name, fire, soil, target in [
        ('constant_match', 0, 0, baseline),
        ('constant_mismatch', 0, 0, .5),
        ('negative_solution', 1, 0, .01),
        ('decreasing_response_equality', -1, 0, .01),
        ('inverse_overflow', 0, 1e-320, .5),
    ]:
        result = rainfall_threshold('M1', 15, T=0, F=fire, S=soil, target_probability=target)
        edge_cases.append(dict(
            name=name, model='M1', duration_minutes=15,
            predictors=dict(T=0, F=fire, S=soil), target_probability=target,
            result=asdict(result),
        ))
    print(json.dumps(dict(
        description='Synthetic supplied predictors; arithmetic evidence, not real-project scientific validation.',
        units=dict(rainfall='mm', intensity='mm/hour', duration='minutes',
                   T='prepared dimensionless terrain predictor',
                   F='M1 normalized dNBR; M3 burned fraction',
                   S='M1 calibrated K convention; M3 mean thickness cm / 254'),
        cases=cases, edge_cases=edge_cases,
    ), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

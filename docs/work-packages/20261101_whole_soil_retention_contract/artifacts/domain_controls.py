"""Exact arithmetic controls; no native execution or physical calibration."""
from fractions import Fraction as F
import json
from pathlib import Path
import sys

def evaluate(por, share, dry, theta_fc, air):
    fc = theta_fc - dry
    ul = por - dry
    candidate = por * share - dry
    drfc = fc + air
    return dict(current_ul=str(ul), volume_scaled_ul=str(candidate),
                fc=str(fc), drfc=str(drfc), current_drainage_denominator=str(ul-drfc),
                candidate_drainage_denominator=str(candidate-drfc),
                current_fc_ul=str(fc/ul), candidate_fc_ul=str(fc/candidate))

counter = evaluate(F(1,2), F(1,2), F(1,16), F(3,16), F(1,16))
assert counter['candidate_drainage_denominator'] == '0'
assert counter['candidate_fc_ul'] == '2/3'
zero = evaluate(F(1,2), F(1), F(1,16), F(3,16), F(1,16))
assert zero['current_ul'] == zero['volume_scaled_ul']
# A positive ratio alone does not protect log(ratio) from a zero logarithm.
assert F(1,2)/F(1,2) == 1
result = dict(passed=True, native_executed=False, controls=3,
              ordered_retention_singular_drainage=counter,
              zero_rock_identity=zero, conductivity_ratio_one_log_zero=True)
with Path(sys.argv[1]).open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')

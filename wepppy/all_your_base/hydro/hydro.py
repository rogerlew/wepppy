import numpy as np
from datetime import datetime, timedelta

def determine_wateryear(y, j=None, mo=None):
    if j is not None:
        mo = int((datetime(int(y), 1, 1) + timedelta(int(j) - 1)).month)

    if int(mo) > 9:
        return int(y) + 1

    return int(y)

def vec_determine_wateryear(y, j=None, mo=None):
    if j is not None:
        if not isinstance(j, np.ndarray):
            j = np.array(j)
        mo = np.vectorize(lambda y, j: int((datetime(int(y), 1, 1) + timedelta(int(j) - 1)).month))(y, j)

    if mo is not None:
        if not isinstance(mo, np.ndarray):
            mo = np.array(mo)

    # Ensure y is a numpy array for consistency in vectorization
    if not isinstance(y, np.ndarray):
        y = np.array(y)

    # Use vectorize to apply the original logic over arrays
    vec_func = np.vectorize(determine_wateryear)
    return vec_func(y, None, mo)


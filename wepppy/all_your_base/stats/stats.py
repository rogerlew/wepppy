import numpy as np


def probability_of_occurrence(return_interval, period_of_interest, pct=True):
    prob = 1.0 - (1.0 - 1.0 / return_interval) ** period_of_interest
    if prob < 0.0:
        prob = 0.0
    elif prob > 1.0:
        prob = 1.0

    if pct:
        prob *= 100.0
    return prob


def weibull_series(recurrence, years, method='cta', gringorten_correction=False):
    """
    Generates a Weibull distribution for return periods based on a given number of years and recurrence intervals.
    
    Args:
        recurrence (list): A list of recurrence intervals (in years) for which to find corresponding ranks.
        years (float): The total number of years for the time series.
        method (str): The method used to calculate the return periods. Options are 'cta' (default) complete time series analysis or 'am' or annual maxima.
        gringorten_correction (bool): If True, applies the Gringorten correction to the Weibull formula.

    Returns:
        dict: A dictionary where keys are the recurrence intervals and values are the ranks in the time series 
              that correspond to the given recurrence intervals.
              
    Explanation:
        The function calculates the recurrence times (return periods) using the Weibull formula, which can be corrected 
        using the Gringorten correction if specified. It then identifies and returns the ranks that correspond to 
        the provided recurrence intervals.
    """
    
    if int(years) <= 0:
        raise ValueError('The number of years must be greater than zero.')

    if method == 'cta':
        # Calculate the total number of days based on the number of years
        n = int(round(years * 365.25))  # 365.25 accounts for leap years
    elif method == 'am':
        n = int(years)
    else:
        raise ValueError('Invalid method. Use "cta" or "am".')

    # Create an array of ranks from 1 to the total number of days
    ranks = np.array(list(range(1, n + 1)))

    # Apply the Weibull formula with or without Gringorten correction
    if gringorten_correction:
        Ts = (n + 1) / (ranks - 0.44)  # Gringorten correction applied
    else:
        Ts = (n + 1) / ranks  # Standard Weibull formula without correction

    if method == 'cta':
        # Convert return periods (Ts) to years by dividing by the number of days in a year
        yearTs = Ts / 365.25
    elif method == 'am':
        yearTs = Ts

    # Initialize a dictionary to store recurrence intervals and their corresponding rank indices
    rec = {}

    # Loop through the sorted recurrence intervals to find corresponding rank indices
    for rec_interval in sorted(recurrence):
        # Reverse the ranks and yearTs arrays to start from the highest values
        for _rank, _yearTs in zip(ranks[::-1], yearTs[::-1]):
            _rank_indx = _rank - 1  # Adjust rank to 0-based index
            # Check if the current return period is greater than or equal to the recurrence interval
            # and if the rank index is not already assigned
            if _yearTs >= rec_interval and _rank_indx not in rec.values():
                rec[rec_interval] = _rank_indx  # Assign the rank index to the recurrence interval
                break  # Move on to the next recurrence interval

    return rec

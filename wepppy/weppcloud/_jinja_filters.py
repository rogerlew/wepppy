"""
Jinja2 Template Filters and Global Functions for WeppPy

This module provides custom filters and global functions for use in Jinja2 templates.

Filters:
--------

zip:
    Combines multiple iterables element-wise.
    Syntax: {{ list1|zip(list2, list3) }}
    Example: {{ ['a', 'b']|zip([1, 2]) }} renders as [('a', 1), ('b', 2)]

sort_numeric:
    Sorts a list by extracting leading numeric values from each element.
    Handles both pure numbers and strings with leading digits.
    Syntax: {{ items|sort_numeric(reverse=False) }}
    Example: {{ ['item10', 'item2', 'item1']|sort_numeric }} renders as ['item1', 'item2', 'item10']
    Example: {{ [3.5, 1.2, 2.8]|sort_numeric(reverse=True) }} renders as [3.5, 2.8, 1.2]

sort_numeric_keys:
    Sorts a dictionary by its keys as integers.
    Syntax: {{ dict|sort_numeric_keys(reverse=False) }}
    Example: {{ {'10': 'ten', '2': 'two', '1': 'one'}|sort_numeric_keys }} 
             renders as [('1', 'one'), ('2', 'two'), ('10', 'ten')]

Global Functions:
----------------

max:
    Returns the maximum value from an iterable or arguments.
    Syntax: {{ max(values) }} or {{ max(a, b, c) }}
    Example: {{ max([1, 5, 3]) }} renders as 5
    Example: {{ max(temperature, threshold) }} compares two variables

min:
    Returns the minimum value from an iterable or arguments.  
    Syntax: {{ min(values) }} or {{ min(a, b, c) }}
    Example: {{ min([1, 5, 3]) }} renders as 1
    Example: {{ min(temperature, threshold) }} compares two variables
"""

import re
from wepppy.all_your_base import isfloat


def sort_numeric_keys(value, reverse=False):
    return sorted(value.items(), key=lambda x: int(x[0]), reverse=reverse)

def extract_leading_digits(s):
    if isfloat(s):
        return float(s)

    match = re.match(r'^(\d+(\.\d+)?)', str(s))
    return float(match.group(1)) if match else 0

def sort_numeric(value, reverse=False):
    return sorted(value, key=extract_leading_digits, reverse=reverse)

def register_jinja_filters(app):
    app.jinja_env.filters['zip'] = zip
    app.jinja_env.filters['sort_numeric'] = sort_numeric
    app.jinja_env.filters['sort_numeric_keys'] = sort_numeric_keys
    app.jinja_env.globals.update(max=max, min=min)

"""
this isn't used by wepppy. hopefully I remember to change this comment if it does get used


"""

import numpy as np
from scipy.interpolate import KroghInterpolator


def polycurve(x, dy):
    #
    # Calculate the y positions from the derivatives
    #
    
    # for each segment calculate the average gradient from the derivatives at each point
    dy = np.array(dy)
    dy_ = np.array([np.mean(dy[i:i+2]) for i in range(len(dy) - 1)])

    # calculate the positions, assume top of hillslope is 0 y
    y = [0]
    for i in range(len(dy) - 1):
        step = x[i+1] - x[i]
        y.append(y[-1] - step * dy_[i])
    y = np.array(y)
    
    assert len(dy) == len(y), '{}, {}, {}'.format(len(x), len(dy), len(y))
    assert dy.shape == y.shape, '{}, {}'.format(dy.shape, y.shape)
    
    xi_k = np.repeat(x, 2)
    yi_k = np.ravel(np.dstack((y, -1*dy)))

    #
    # Return the model
    #
    return KroghInterpolator(xi_k, yi_k)


def calc_ermit_grads(hillslope_model):
    p = hillslope_model
    assert p.xi[0] == 0.0
    assert p.xi[-1] == 1.0
    
    y1 = p(0.1)
    y0 = p(0.0)
    top = -(y1 - y0) / 0.1
    
    y1 = p(0.9)
    y0 = p(0.1)
    middle = -(y1 - y0) / 0.8
    
    y1 = p(1.0)
    y0 = p(0.9)
    bottom = -(y1 - y0) / 0.1
    
    return top, middle, bottom


def calc_disturbed_grads(hillslope_model):
    p = hillslope_model
    assert p.xi[0] == 0.0
    assert p.xi[-1] == 1.0
    
    y1 = p(0.25)
    y0 = p(0.0)
    upper_top = -(y1 - y0) / 0.25
    
    y1 = p(0.50)
    y0 = p(0.25)
    upper_bottom = -(y1 - y0) / 0.25
    
    y1 = p(0.75)
    y0 = p(0.50)
    lower_top = -(y1 - y0) / 0.25
    
    y1 = p(1.00)
    y0 = p(0.75)
    lower_bottom = -(y1 - y0) / 0.25
    
    return upper_top, upper_bottom, lower_top, lower_bottom


if __name__ is "__main__":

    def rel_elevations(x, dy):
        assert len(x) == len(dy)

        # calculate the positions, assume top of hillslope is 0 y
        y = [0]
        for i in range(len(dy) - 1):
            step = x[i + 1] - x[i]
            y.append(y[-1] - step * dy[i])
        y = np.array(y)

        return y


    length = 756.3961030678929
    distance_p = [
        0.0,
        0.0594232599747543,
        0.11884651994950861,
        0.1782697799242629,
        0.2376930398990172,
        0.29711629987377147,
        0.3565395598485258,
        0.4159628198232801,
        0.47538607979803443,
        0.5174046698863943,
        0.5768279298611486,
        0.636251189835903,
        0.6782697799242629,
        0.7376930398990172,
        0.7797116299873771,
        0.8391348899621315,
        0.8985581499368858,
        0.9405767400252457,
        1.0
    ]

    slopes = [
        0.2922700047492981,
        0.44547998905181885,
        0.2663399875164032,
        0.33469998836517334,
        0.4360499978065491,
        0.30169999599456787,
        0.2899099886417389,
        0.2451300024986267,
        0.17913000285625458,
        0.16666999459266663,
        0.26162999868392944,
        0.2828400135040283,
        0.3433299958705902,
        0.24041999876499176,
        0.14000000059604645,
        0.1084199994802475,
        0.146139994263649,
        0.09000000357627869,
        0.1319900006055832
    ]
    print(rel_elevations(distance_p, slopes))

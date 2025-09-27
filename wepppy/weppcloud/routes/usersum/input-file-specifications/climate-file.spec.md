# Climate Input File Specification

- Line 1:

  CLIGEN version number - real (datver)
    - 0.0 - use actual storm ip values in this file
    - 4.0 - WEPP will internally multiply ip by a factor of 0.70 to compensate for the steady-state erosion model assumption.
    - 4.30 – Reference to which version of CLIGEN generated this file
    - 5.30 - Reference to which version of CLIGEN generated this file

- Line 2:

  a) simulation mode - integer (itemp)
    - 1 - continuous
    - 2 - single storm

  b) breakpoint data flag - integer (ibrkpt)
    - 0 - no breakpoint data used
    - 1 - breakpoint data used

  c) wind information/ET equation flag - integer (iwind)
    - 0 - wind information exists - use Penman ET equation
    - 1 - no wind information exists - use Priestley-Taylor ET equation

- Line 3:

  a) station i.d. and other information - character (stmid)

- Line 4:

  variable name headers

- Line 5:

  a) degrees latitude (+ is North, - is South) - real (deglat)

  b) degrees longitude (+ is East, - is West) - real (deglon)

  c) station elevation (m) - real (elev)

  d) weather station years of observation - integer (obsyrs)

  e) beginning year of CLIGEN simulation - integer (ibyear)

  f) number of climate years simulated and in file - integer (numyr)

  g) command line that was used to run CLIGEN (version 5.1+ only)

- Line 6:

  monthly maximum temperature variable name header

- Line 7: 

  observed monthly average maximum Temp. (degrees C) - real (obmaxt)

- Line 8:

  monthly minimum temperature variable name header

- Line 9:

  observed monthly average minimum Temp. (degrees C) - real (obmint)

- Line 10:

  monthly average daily solar radiation variable name header

- Line 11:

  observed monthly average daily solar radiation (langleys) - real (radave)

- Line 12:

  monthly average precipitation variable name header

- Line 13: 

  observed monthly average precipitation ( mm) - real (obrain)

- Line 14: 

  daily variables name header

- Line 15: 

  daily variables' dimensions

**For CLIGEN generated (no breakpoint data) input option**

- Line 16: _(repeated for the number of simulation days)_

  a) day of simulation - integer (day)

  b) month of simulation - integer (mon)

  c) year of simulation - integer (year)

  d) daily precipitation amount (mm of water) - real (prcp)

  e) duration of precipitation (hr) - real (stmdur)

  f) ratio of time to rainfall peak/rainfall duration - real (timep)

  g) ratio of maximum rainfall intensity/average rainfall intensity - real (ip)

  h) maximum daily temperature (degrees C) - real (tmax)

  i) minimum daily temperature (degrees C) - real (tmin)

  j) daily solar radiation (langleys/day) - real (rad)

  k) wind velocity (m/sec) - real (vwind)

  l) wind direction (degrees from North) - real (wind)

  m) dew point temperature (degrees C) - real (tdpt)

  **For breakpoint precipitation input option**

  _Lines 16 & 17 are repeated for the number of simulation days._

- Line 16: 

  a) day of simulation - integer (day)

  b) month of simulation - integer (mon)

  c) year of simulation - integer (year)

  d) number of breakpoints - integer (nbrkpt)

  e) maximum daily temperature (degrees C) - real (tmax)

  f) minimum daily temperature (degrees C) - real (tmin)

  g) daily solar radiation (langleys/day) - real (rad)

  h) wind velocity (m/sec) - real (vwind)

  i) wind direction (degrees from North) - real (wind)

  j) dew point temperature (degrees C) - real (tdpt)

- Line 17: _(repeated for number of breakpoints, maximum of 50 points/day)_

  a) time after midnight (hours) - real (timem)

  b) cumulative precipitation at this time (mm of water)- real (pptcum)

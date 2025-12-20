# Format of CLIGEN Weather Station Statistics Input Files

**Version:** CLIGEN versions 4.1 - 5.1 (as of 6/2001)  
**Updated:** 12/11/2008 by Jim Frankenberger  
**Original Compilation:** Dennis C. Flanagan (USDA-ARS NSERL), Mark A. Nearing (USDA-ARS NSERL), Jeff G. Arnold (USDA-ARS Grassland, Soil/Water Research Lab).

> **Important Update (12/11/2008):** The units for wind velocity and wind velocity standard deviation were incorrect (mph) in the previous version of the documentation. The correct units for wind velocity and wind velocity standard deviation are **m/s**.

---

## Line 1: Station Identification

**Variables:**
*   `Station name`: (41 characters)
*   `State id number`: (Integer)
*   `Station id number`: (Integer)
*   `igcode`: 2 digit code (read but not used in CLIGEN)

**Fortran Read/Format:**
```fortran
read(10,450,end=40)stidd,nst,nstat,igcode
450 format(a41,i2,i4,i2)
```

**Example:**
```text
DELPHI IN                                122149 0
```

---

## Line 2: Station Location & Record Info
## Line 3: Elevation & Precipitation Extremes

**Line 2 Variables:**
*   `Latitude`
*   `Longitude`
*   `Station years of record`
*   `itype`: Integer value from 1-4 to set single storm parameters

**Line 3 Variables:**
*   `Elevation`: Elevation above sea level (ft)
*   `TP5`: Maximum 30 minute precipitation depth (inches) (not read by CLIGEN)
*   `TP6`: Maximum 6 hour precipitation depth (inches)

> Both TP5 and TP6 values were obtained from "Hershfield, 1961. Rainfall frequency atlas of the US for durations of 30 minutes to 24 hours and return periods from 1 to 100 years. U.S. Dept. of Commerce Tech. Paper No. 40."

**Fortran Read/Format:**
```fortran
read(10,470)ylt,yll,years,itype,elev,tp6
470 format(6x,f7.2,6x,f7.2,7x,i3,7x,i2/12x,i5,17x,f5.2)
```

**Example:**
```text
LATT=   40.58 LONG=  -86.67 YEARS=  44. TYPE=  3
ELEVATION =   670. TP5 =  2.17 TP6=  4.22
```

---

## Line 4: Mean Daily Precipitation
## Line 5: Standard Deviation of Daily Precipitation
## Line 6: Skew Coefficient of Daily Precipitation

**Line 4 Description:** Mean liquid equivalent precipitation depth (inches) for a day precipitation occurs (by month).
*   *Calculation:* Average total precipitation for the month divided by the number of days in which precipitation occurs.

**Line 5 Description:** Standard deviation of daily precipitation value (inches) (by month).

**Line 6 Description:** Skew coefficient of daily precipitation value (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(rst(i,1),i=1,12),(rst(i,2),i=1,12),(rst(i,3),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
MEAN P    0.23  0.25  0.26  0.31  0.35  0.41  0.49  0.45  0.39  0.33  0.30  0.28
S DEV P   0.32  0.34  0.30  0.40  0.42  0.53  0.59  0.58  0.53  0.42  0.37  0.34
SQEW P    3.39  3.18  1.98  4.06  2.17  2.52  1.95  2.39  3.48  2.42  2.38  2.41
```

---

## Line 7: Probability of Wet Day following Wet Day
## Line 8: Probability of Wet Day following Dry Day

**Description:** Probability values (between 0.0 and 1.0) by month. A wet day is defined as a day with nonzero precipitation.

**Fortran Read/Format:**
```fortran
read(10,480)(prw(1,i),i=1,12),(prw(2,i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
P(W/W)    0.42  0.37  0.43  0.54  0.52  0.45  0.39  0.41  0.38  0.45  0.47  0.43
P(W/D)    0.23  0.24  0.28  0.29  0.25  0.26  0.24  0.21  0.20  0.20  0.24  0.24
```

---

## Line 9: Mean Maximum Daily Air Temperature

**Description:** Degrees Fahrenheit (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(obmx(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
TMAX AV 34.49 38.81 50.19 63.87 74.55 83.23 86.16 83.95 78.23 66.73 51.62 38.64
```

---

## Line 10: Mean Minimum Daily Air Temperature

**Description:** Degrees Fahrenheit (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(obmn(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
TMIN AV 17.63 20.82 29.91 40.05 49.88 59.18 62.78 60.53 53.50 42.52 33.04 22.80
```

---

## Line 11: Standard Deviation of Max Temperature
## Line 12: Standard Deviation of Min Temperature

**Description:** Standard deviation for daily maximum/minimum temperatures in degrees Fahrenheit (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(stdtx(i),i=1,12),(stdtm(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
SD TMAX 12.07 11.34 12.41 11.34  9.30  7.20  5.75  5.77  8.36 10.22 11.76 11.47
SD TMIN 13.10 12.31 10.60  9.86  9.21  7.66  6.60  7.20  9.46  9.85 10.47 12.11
```

---

## Line 13: Mean Daily Solar Radiation

**Description:** Langleys (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(obsl(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
SOL.RAD  125.  189.  286.  373.  465.  514.  517.  461.  374.  264.  156.  111.
```

---

## Line 14: Standard Deviation for Daily Solar Radiation

**Description:** Langleys (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(stdsl(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
SD SOL   51.7  63.8  79.0 100.2 104.8 103.5  93.9 182.1  82.7  49.8  47.8  46.9
```

---

## Line 15: Mean Max Daily 30-min Precipitation Intensity

**Description:** inches/hour (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(wi(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
MX .5 P  0.44  0.45  0.45  0.95  0.63  1.91  1.46  1.59  1.02  0.57  0.32  0.42
```

---

## Line 16: Mean Daily Dew Point Temperature

**Description:** Degrees Fahrenheit (by month).

**Fortran Read/Format:**
```fortran
read(10,480)(rh(i),i=1,12)
480 format(8x,12f6.2)
```

**Example:**
```text
DEW PT  22.54 23.27 29.64 39.64 49.08 59.35 63.67 62.67 54.38 44.69 32.60 24.18
```

---

## Line 17: Time to Peak Rainfall Intensity (Cumulative Distribution)

**Description:**
These 12 values represent a cumulative distribution of computed time to peak rainfall intensity (`Tp`) values based upon the National Weather Service 15 minute rainfall data.
The 12 values in columns 1-12 represent respectively the fraction of computed Tp values between:
0.0-0.0833, 0.0833-0.1667, 0.1667-0.25, 0.25-0.3333, 0.3333-0.4167, 0.4167-0.5, 0.5-0.5833, 0.5833-0.6667, 0.6667-0.75, 0.75-0.8333, 0.8333-0.9167, and 0.9167-1.0.

*Note:* To obtain the `Tp` value from the NWS data, all inter-storm periods of zero precipitation are first removed (storms are collapsed), and `Tp` is computed as the ratio of (elapsed time from the beginning of the first precipitation interval to the mid-point of the 15 minute interval containing the peak intensity) to (total time from the beginning of the first precipitation interval to the end of the last precipitation interval). See section 2.1.4 in the WEPP Technical Documentation (Flanagan and Nearing, 1995).

**Fortran Read/Format:**
```fortran
read(10,485)(timpkd(i),i=1,12)
485 format(8x,12f6.3)
```

**Example:**
```text
Time Pk  0.652 0.746 0.789 0.830 0.845 0.857 0.873 0.893 0.903 0.930 0.961 1.000
```

---

## Lines 18-81: Wind Information

**General Format:**
All wind lines follow the same read and format structure. They are grouped by direction (16 directions total).

**Fortran Read/Format:**
```fortran
read(10,1250)(((wvl(i,j,k),k=1,12),j=1,4),i=1,16)
1250 format(8x,12f6.2)
```

For each direction, there are 4 lines of data (by month):
1.  Percentage of time wind from that direction.
2.  Average wind velocity (m/s).
3.  Standard deviation of winds (m/s).
4.  Skew coefficient of wind data.

### Directions

1.  **North (N)** (Lines 18-21)
2.  **North-North-East (NNE)** (Lines 22-25)
3.  **North-East (NE)** (Lines 26-29)
4.  **East-North-East (ENE)** (Lines 30-33)
5.  **East (E)** (Lines 34-37)
6.  **East-South-East (ESE)** (Lines 38-41)
7.  **South-East (SE)** (Lines 42-45)
8.  **South-South-East (SSE)** (Lines 46-49)
9.  **South (S)** (Lines 50-53)
10. **South-South-West (SSW)** (Lines 54-57)
11. **South-West (SW)** (Lines 58-61)
12. **West-South-West (WSW)** (Lines 62-65)
13. **West (W)** (Lines 66-69)
14. **West-North-West (WNW)** (Lines 70-73)
15. **North-West (NW)** (Lines 74-77)
16. **North-North-West (NNW)** (Lines 78-81)

**Example (North):**
```text
% N       3.80  5.16  5.32  5.43  5.82  6.28  6.11  6.42  5.25  4.57  3.25  2.41
MEAN      5.08  5.34  5.22  5.06  4.62  3.91  3.65  3.62  4.27  4.30  4.76  4.85
STD DEV   1.74  2.21  2.13  2.09  2.09  1.70  1.55  1.51  1.67  1.77  2.14  2.15
SKEW      0.24  0.33  0.48  0.47  0.54  0.49  0.49  0.42  0.40  0.30  0.29  0.62
```

---

## Line 82: Calm Conditions

**Description:** Percentage of time there are calm conditions (by month).

**Fortran Read/Format:**
```fortran
read(10,1250)(calm(i),i=1,12)
1250 format(8x,12f6.2)
```

**Example:**
```text
CALM      2.73  2.26  2.59  2.32  3.93  6.95  8.66 10.11  8.17  7.48  3.77  2.97
```

---

## Line 83: Interpolation Stations

**Description:** Stations from which wind data was interpolated and weighting factor assigned to each station.
*Note:* Values are not used internally in CLIGEN.

**Fortran Read/Format:**
```fortran
read(10,1260)site(1),wgt(1),site(2),wgt(2),site(3),wgt(3)
1260 format(a19,f6.3,2(2x,a19,f6.3))
```

**Example:**
```text
W. LAFAYETTE       IN  0.549  BUNKER HILL        IN  0.326  SOUTH BEND         IN  0.124
```

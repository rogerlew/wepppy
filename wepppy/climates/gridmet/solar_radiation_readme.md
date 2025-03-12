
### Converting Daily Mean Downward Shortwave Radiation from W/m² to Langleys per Day (l/day)

This markdown provides a clear, step-by-step explanation of how to convert daily mean downward shortwave radiation, given in watts per square meter (W/m²), to langleys per day (l/day). A langley is a unit of energy equal to one calorie per square centimeter (cal/cm²).

---

#### Step 1: Define the Daily Mean (W/m²)
- The **Daily Mean** is the average shortwave radiation flux over a 24-hour period, measured in watts per square meter (W/m²).
- Since 1 watt (W) = 1 joule per second (J/s), the units can be expressed as:
    ```
    Daily Mean = J / (s · m²)
    ```

---

#### Step 2: Calculate Total Energy per Day (J/m²)
- To find the total energy received over a day, multiply the Daily Mean by the number of seconds in a day (24 hours × 60 minutes × 60 seconds = 86,400 seconds):
    ```
    Total Energy = Daily Mean × 86,400
    ```
- **Units**:
    ```
    (J / (s · m²)) × (s/day) = J / (m² · day)
    ```
- This gives the total energy in joules per square meter per day (J/m²/day).

---

#### Step 3: Define Langleys per Day (l/day)
- A **langley (l)** is equal to 1 calorie per square centimeter (cal/cm²):
    ```
    1 l = 1 cal/cm²
    ```
- For a daily total, langleys per day is:
    ```
    l/day = cal / (cm² · day)
    ```

---

#### Step 4: Convert J/m² to cal/cm²
- Convert joules to calories and square meters to square centimeters:
    - **Energy**: 1 calorie = 4.184 joules, so:
    ```
    1 J = 1 / 4.184 cal
    ```
    - **Area**: 1 m² = 10,000 cm², so:
    ```
    1 / m² = 1 / 10,000 cm⁻²
    ```
- Combine these conversions:
    ```
    Total Energy in cal/cm² = (Total Energy in J/m²) × (1 / 4.184 cal/J) × (1 / 10,000 m²/cm²)
                            = (Total Energy in J/m²) / (4.184 × 10,000)
                            = (Total Energy in J/m²) / 41,840
    ```

---

#### Step 5: Derive the Final Conversion Formula
- Substitute the Total Energy from Step 2:
    ```
    l/day = (Daily Mean × 86,400) / 41,840
    ```
- Simplify the constant:
    ```
    86,400 / 41,840 ≈ 2.0645
    ```
- Thus, the approximate formula is:
    ```
    l/day ≈ Daily Mean × 2.0645
    ```
- **Units check**:
    ```
    [(J / (s · m²)) × (s/day)] / [41,840 (J/m²)/(cal/cm²)] = cal / (cm² · day)
    ```
- This matches the units of langleys per day.

---

#### Example
- If the Daily Mean is 200 W/m²:
    - Total Energy = 200 × 86,400 = 17,280,000 J/m²
    - l/day = 17,280,000 / 41,840 ≈ 413.0019 l/day
    - Using the approximate factor: 200 × 2.0645 ≈ 412.9 l/day
- The exact calculation (413.0019) is preferred for precision.

---

#### Final Formula
To convert Daily Mean (W/m²) to langleys per day (l/day):
```
l/day = (Daily Mean × 86,400) / 41,840
```
Or, approximately:
```
l/day ≈ Daily Mean × 2.0645
```

This conversion accounts for both the time integration (seconds per day) and the unit conversions (joules to calories and m² to cm²).

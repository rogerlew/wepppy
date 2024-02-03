import pandas as pd

columns_for_imputation = [
    'Air Temperature Maximum (degF)',
    'Air Temperature Minimum (degF)',
    'Air Temperature Average (degF)']


def process_snotel(historic_fn, processed_fn, start_year=1984, end_year=2023):
    global columns_for_imputation

    # Find the start of the actual data (after metadata)
    with open(historic_fn, 'r') as file:
        for i, line in enumerate(file):
            if not line.startswith('#'):
                header_line = i
                break

    # Read the CSV into a DataFrame
    df = pd.read_csv(historic_fn, skiprows=header_line, parse_dates=[0], na_values=['', ' '])

    imputed_df = df.copy()
    for col in columns_for_imputation:
        imputed_df[col] = imputed_df[col].interpolate(method='linear')

    # Adding a 'Year' column to the DataFrame
    imputed_df['Year'] = imputed_df['Date'].dt.year

    # apply start_year filter
    imputed_df = imputed_df[imputed_df['Year'] >= start_year]

    imputed_df = imputed_df[imputed_df['Year'] <= end_year]

    # Filtering the DataFrame to include only valid years
    # A valid year is defined as a year with data for every day of the year and Precipitation Accumulation on at least 1 day

    # Grouping the DataFrame by 'Year' and applying the conditions
    valid_years = imputed_df.groupby('Year').apply(
        lambda x: (x['Date'].dt.date.is_unique and len(x) == 365 or len(x) == 366) and
                  x['Precipitation Accumulation (in) Start of Day Values'].notna().any()
    ).index[imputed_df.groupby('Year').apply(
        lambda x: (x['Date'].dt.date.is_unique and len(x) == 365 or len(x) == 366) and
                  x['Precipitation Accumulation (in) Start of Day Values'].notna().any()
    )]

    # Displaying the valid years
    valid_years.tolist()

    # Check for non-consecutive years in the valid_years list
    non_consecutive_years = [year for i, year in enumerate(valid_years) if i > 0 and year != valid_years[i - 1] + 1]

    if non_consecutive_years:
        print(f'Non-consecutive valid years detected: {non_consecutive_years}')


    first_full_year = min(valid_years)
    imputed_df = imputed_df[imputed_df['Year'] >= first_full_year]


    precipitation_counts = imputed_df.groupby('Year')['Precipitation Accumulation (in) Start of Day Values']\
                                     .apply(lambda x: x.notna().sum()).to_dict()

    imputed_df = imputed_df.drop(columns=['Year'])
    imputed_df.to_csv(processed_fn, index=False)

    return precipitation_counts


if __name__ == "__main__":
    from glob import glob
    from os.path import join as _join
    from os.path import split as _split
    from pprint import pprint

    historic_fns = glob('historic/*.csv')

    for historic_fn in historic_fns:

        _dir, fn = _split(historic_fn)
        processed_fn = _join('processed', fn)

        d = process_snotel(historic_fn, processed_fn)
        d = {k:v for k,v in d.items() if v < 365}
        if len(d) > 0:
            print(historic_fn, d)

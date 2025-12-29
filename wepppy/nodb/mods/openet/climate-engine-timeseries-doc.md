.. sectionauthor:: Jody Hansen <jody.hansen at dri.edu>

Timeseries
==========

| The Timeseries endpoints are used to generate time series data for the datasets available in Climate Engine.

| There are three groups of Timeseries endpoints for points, polygons or an Earth Engine FeaturesCollection:

| **/timeseries/native** - The native endpoints are used to generate 'raw' time series data.
| **/timeseries/interannual** - The interannual endpoints are used to generate time series of yearly values of the dataset variable summarized over a season.
| **/timeseries/regression** - The regression endpoints are used to perform regression analysis of the dataset variable summarized over a season.

| **NOTES:**
| - The 'forecasts' endpoints are only available for forecast datasets CFS_GRIDMET, FRET, GEPS_2WK, "GEPS_4WK.


| :ref:`RST /timeseries/native/coordinates`
| :ref:`RST /timeseries/native/feature_collection`
| :ref:`RST /timeseries/native/forecasts/coordinates`
| :ref:`RST /timeseries/native/forecasts/feature_collection`
| :ref:`RST /timeseries/standard_index/coordinates`
| :ref:`RST /timeseries/standard_index/feature_collection`
| :ref:`RST /timeseries/interannual/coordinates`
| :ref:`RST /timeseries/interannual/feature_collection`
| :ref:`RST /timeseries/regression/coordinates`
| :ref:`RST /timeseries/regression/feature_collection`


.. _RST /timeseries/native/coordinates:

/timeseries/native/coordinates
******************************
| Generates timeseries of values of the dataset variable and timeperiod between start_date and end_date for points or polygons.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/native/coordinates?dataset=GRIDMET&variable=pr&start_date=2014-01-01&end_date=2014-02-01&coordinates=[[-119.96,39.57]]

.. list-table:: 
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - coordinates
     - yes
     - List of point or polygon coordinates, see https://support.climateengine.org/article/152-formatting-coordinates-for-api-requests
     -
     - [[-119.96,39.57]]
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     - single or multiple variable
     -
     - NDVI or NDVI,EVI
   * - compute_trends
     - no
     - Also compute trends
     -
     - sens_slope, polyfit
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_date
     - yes
     -
     -
     - 2019-01-01
   * - end_date
     - yes
     -
     -
     - 2019-12-31
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/native/feature_collection:

/timeseries/native/feature_collection
*************************************
| Generates timeseries of values of the dataset variable and timeperiod between start_date and end_date for the features of an Earth Engine FeatureCollection.
| The values are averaged over the pixels lying within each feature of the feature collection.
| Permissions on the asset must be such that it is readable by anyone.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/native/feature_collection?dataset=LANDSAT7_TOA&variable=NDVI&start_date=2014-01-01&end_date=2014-02-01&feature_collection_asset_id=WCMC/WDPA/current/points&sub_choices= ["Golden Gate"]&filter_by=NAME

.. list-table::
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - feature_collection_asset_id
     - yes
     - EE FeatureCollection asset id, must have "Anyone can read" permissions
     -
     - WCMC/WDPA/current/points
   * - sub_choices
     - no
     - List of features to use in analysis, must be strings
     -
     - ["Golden Gate"]
   * - filter_by
     - no
     - Property name to filter sub-choices
     -
     - NAME
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max, stdev, count, count_un, skew, kurtosis, percentile_5, percentile_10, percentile_25, percentile_75, percentile_90, percentile_95
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     - single or multiple variable
     -
     - NDVI or NDVI,EVI
   * - compute_trends
     - no
     - Also compute trends
     -
     - sens_slope, polyfit
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_date
     - yes
     -
     -
     - 2019-01-01
   * - end_date
     - yes
     -
     -
     - 2019-12-31
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/native/forecasts/coordinates:

/timeseries/native/forecasts/coordinates
****************************************
| Generates timeseries of forecast values of the dataset variable and timeperiod between start_date and end_date for points or polygons.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/native/forecasts/coordinates?dataset=CFS_GRIDMET&variable=pr&start_day=day01&end_day=day28&coordinates=[[-119.96,39.57]]

.. list-table::
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - coordinates
     - yes
     - List of point or polygon coordinates, see https://support.climateengine.org/article/152-formatting-coordinates-for-api-requests
     -
     - [[-119.96,39.57]]
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     -
     - CFS_GRIDMET
     - CFS_GRIDMET, FRET, GEPS_2WK,GEPS_4WK
   * - variable
     - yes
     - pet, pr, tmmn, tmmx
     -
     - pr
   * - model
     - yes
     - ens01 to en<xx> for individual models (see documentation), ens_min, ens_max, ens_mean, ens_median
     - ens_mean
     - ens_max
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/native/forecasts/feature_collection:

/timeseries/native/forecasts/feature_collection
***********************************************
| Generates timeseries of forecast values of the dataset variable and timeperiod between start_date and end_date for the features of an Earth Engine FeatureCollection.
| The values are averaged over the pixels lying within each feature of the feature collection.
| Permissions on the asset must be such that it is readable by anyone.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/native/forecasts/feature_collection?dataset=CFS_GRIDMET&variable=pet&start_day=day01&end_day=day28&feature_collection_asset_id=WCMC/WDPA/current/points&sub_choices= ["Golden Gate"]&filter_by=NAME

.. list-table::
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - feature_collection_asset_id
     - yes
     - EE FeatureCollection asset id, must have "Anyone can read" permissions
     -
     - WCMC/WDPA/current/points
   * - sub_choices
     - no
     - List of features to use in analysis, must be strings
     -
     - ["Golden Gate"]
   * - filter_by
     - no
     - Property name to filter sub-choices
     -
     - NAME
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max, stdev, count, count_un, skew, kurtosis, percentile_5, percentile_10, percentile_25, percentile_75, percentile_90, percentile_95
   * - dataset
     - yes
     -
     - CFS_GRIDMET
     - CFS_GRIDMET, FRET, GEPS_2WK,GEPS_4WK
   * - variable
     - yes
     - pet, pr, tmmn, tmmx
     -
     - pet
   * - model
     - yes
     - ens01 to en<xx> for individual models (see documentation), ens_min, ens_max, ens_mean, ens_median
     - ens_mean
     - ens_max
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/standard_index/coordinates:

/timeseries/standard_index/coordinates
**************************************
| Generates timeseries of standard index based on inputs for points or polygons.
| Standard Precipitation Index (SPI) for example is the standard index of precipitation. To calculate SPI, you would use precipitation as the variable.
| Similarly, the Standardized Precipitation Evapotranspiration Index (SPEI) potential water deficit (precipitation minus potential evapotranspiration) would be used as the variable.
| In the case of a buffer, the values are reduced over the pixels lying within the point before calculating the standard index.
| Note: Cannot use pre-calculated drought indices, i.e. GridMET Drought as dataset/variable.
| Available variables: spi, spei, eddi, speih, edddih
| Returns: json

Resource url example:

.. code-block::

    /timeseries/standard_index/coordinates?dataset=PRISM_MONTHLY&variable=ppt&area_reducer=mean&start_date=1991-01-01&end_date=2020-12-31&start_year=1991&end_year=2020&accumulation=3&distribution=loglogistic&coordinates=%5B%5B-121.61%2C38.78%5D%5D

.. list-table::
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - coordinates
     - yes
     - List of point or polygon coordinates, see https://support.climateengine.org/article/152-formatting-coordinates-for-api-requests
     -
     - [[-121.61,38.78]]
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     - Dataset of interest
     - PRISM_MONTHLY
     - PRISM_MONTHLY, GRIDMET
   * - variable
     - yes
     - Variable of interest
     - spi
     - spi, spei, eddi, speih, eddih
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_date
     - yes
     - Start date for timeseries
     - 1991-01-01
     - 2019-01-01
   * - end_date
     - yes
     - End date for timeseries
     - 2020-12-31
     - 2019-12-31
   * - start_year
     - yes
     - Start year for climatology
     - 1991
     - 1990
   * - end_year
     - yes
     - End year for climatology
     - 2020
     - 2020
   * - accumulation
     - yes
     - Accumulation period for index. Same unit as dataset.
     - 3
     - 3, 30, 12, 365
   * - distribution
     - yes
     - The distribution used to calculate the standard index
     - loglogistic
     - loglogistic, gamma, nonparametric
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/standard_index/feature_collection:

/timeseries/standard_index/feature_collection
*********************************************
| Generates timeseries of standard index based on inputs for an Earth Engine FeatureCollection.
| Standard Precipitation Index (SPI) for example is the standard index of precipitation. To calculate SPI, you would use precipitation as the variable.
| Similarly, the Standardized Precipitation Evapotranspiration Index (SPEI) potential water deficit (precipitation minus potential evapotranspiration) would be used as the variable.
| The values are reduced over the pixels lying within the feature before calculating the standard index.
| Note: Cannot use pre-calculated drought indices, i.e. GridMET Drought as dataset/variable.
| Available variables: spi, spei, eddi, speih, edddih
| Returns: json

Resource url example:

.. code-block::

    /timeseries/standard_index/feature_collection?dataset=PRISM_MONTHLY&variable=ppt&area_reducer=mean&start_date=1991-01-01&end_date=2020-12-31&start_year=1991&end_year=2020&accumulation=3&distribution=loglogistic&feature_collection_asset_id=USGS%2FWBD%2F2017%2FHUC08

.. list-table::
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - feature_collection_asset_id
     - yes
     - EE FeatureCollection asset id, must have "Anyone can read" permissions
     - USGS/WBD/2017/HUC08
     -
   * - sub_choices
     - no
     - List of features you are interested in
     -
     - Piscataqua-Salmon Falls
   * - filter_by
     - no
     - Name of the property you want to filter by
     -
     - name
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Reducer over the polygon
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     - Dataset of interest
     - PRISM_MONTHLY
     - PRISM_MONTHLY, GRIDMET
   * - variable
     - yes
     - Variable of interest
     - spi
     - spi, spei, eddi, speih, edddih
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_date
     - yes
     - Start date for timeseries
     - 1991-01-01
     - 2019-01-01
   * - end_date
     - yes
     - End date for timeseries
     - 2020-12-31
     - 2019-12-31
   * - start_year
     - yes
     - Start year for climatology
     - 1991
     - 1990
   * - end_year
     - yes
     - End year for climatology
     - 2020
     - 2020
   * - accumulation
     - yes
     - Accumulation period for index. Same unit as dataset.
     - 3
     - 3, 30, 12, 365
   * - distribution
     - yes
     - The distribution used to calculate the standard index
     - loglogistic
     - loglogistic, gamma, nonparametric
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/interannual/coordinates:

/timeseries/interannual/coordinates
***********************************
| Generates timeseries of yearly values of the dataset variable summarized over a season for points or polygons.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/interannual/coordinates?dataset=LANDSAT7_TOA&variable=NDVI&temporal_statistic=Mean&start_day=01&end_day=30&start_month=01&end_month=12&start_year=2016&end_year=2018&coordinates=[[-119.96,39.57], [-119, 39]]

.. list-table:: 
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - coordinates
     - yes
     - List of point or polygon coordinates, see https://support.climateengine.org/article/152-formatting-coordinates-for-api-requests
     -
     - [[-119.96,39.57]]
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     - single or multiple variable
     -
     - NDVI or NDVI,EVI
   * - compute_trends
     - no
     - Also compute trends
     -
     - sens_slope, polyfit
   * - temporal_statistic
     - yes
     -
     -
     - mean
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_day
     - yes
     -
     -
     - 01
   * - end_day
     - yes
     -
     -
     - 30
   * - start_month
     - yes
     -
     -
     - 01
   * - end_month
     - yes
     -
     -
     - 12
   * - start_year
     - yes
     -
     -
     - 2016
   * - end_year
     - yes
     -
     -
     - 2018
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/interannual/feature_collection:

/timeseries/interannual/feature_collection
******************************************
| Generates timeseries of yearly values of the dataset variable summarized over a season for the features of an Earth Engine FeatureCollection.
| The values are averaged over the pixels lying within each feature of the feature collection.
| Permissions on the asset must be such that it is readable by anyone.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/interannual/feature_collection?dataset=LANDSAT7_TOA&variable=NDVI&temporal_statistic=Mean&start_day=01&end_day=30&start_month=01&end_month=12&start_year=2014&end_year=2018&feature_collection_asset_id=WCMC/WDPA/current/points&sub_choices=["Golden Gate"]&filter_by=NAME

.. list-table:: 
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - feature_collection_asset_id
     - yes
     - EE FeatureCollection asset id, must have "Anyone can read" permissions
     -
     - WCMC/WDPA/current/points
   * - sub_choices
     - no
     - List of features to use in analysis, must be strings
     -
     - ["Golden Gate"]
   * - filter_by
     - no
     - Property name to filter sub-choices
     -
     - NAME
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max, stdev, count, count_un, skew, kurtosis, percentile_5, percentile_10, percentile_25, percentile_75, percentile_90, percentile_95
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     - single or multiple variable
     -
     - NDVI or NDVI,EVI
   * - compute_trends
     - no
     - Also compute trends
     -
     - sens_slope, polyfit
   * - temporal_statistic
     - yes
     -
     -
     - mean, median, max, min, total
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_day
     - yes
     -
     -
     - 01
   * - end_day
     - yes
     -
     -
     - 30
   * - start_month
     - yes
     -
     -
     - 01
   * - end_month
     - yes
     -
     -
     - 12
   * - start_year
     - yes
     -
     -
     - 2016
   * - end_year
     - yes
     -
     -
     - 2018
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json


.. _RST /timeseries/regression/coordinates:

/timeseries/regression/coordinates
**********************************
| Performs regression analysis of the dataset variable summarized over a season for points or polygons.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/regression/coordinates?dataset=LANDSAT7_TOA&variable=NDVI&temporal_statistic=Mean&var2_dataset=LANDSAT7_TOA&var2_variable=NDSI&var2_temporal_statistic=Mean&start_day=01&end_day=30&start_month=01&end_month=12&var2_start_day=01&var2_end_day=30&var2_start_month=01&var2_end_month=12&start_year=2016&end_year=2018&coordinates=[[-119.96,39.57]]

.. list-table:: 
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - coordinates
     - yes
     - List of point or polygon coordinates, see https://support.climateengine.org/article/152-formatting-coordinates-for-api-requests
     -
     - [[-119.96,39.57]]
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - buffer
     - no
     - List of integer buffers (meters) to be applied to each geometry
     -
     - [400]
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - 
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     -
     -
     - NDVI
   * - mask_image_id
     - no
     - Image mask ID
     -
     -
   * - mask_band
     - no
     - Mask band
     -
     -
   * - mask_value
     - no
     - Image mask value
     -
     -
   * - start_day
     - yes
     -
     -
     - 01
   * - end_day
     - yes
     -
     -
     - 30
   * - start_month
     - yes
     -
     -
     - 01
   * - end_month
     - yes
     -
     -
     - 12
   * - temporal_statistic
     - yes
     -
     -
     - mean, median, max, min, total
   * - var2_dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - var2_variable
     - yes
     -
     -
     - NDSI
   * - var2_mask_image_id
     - no
     - Image mask ID for the second dataset/variable
     -
     -
   * - var2_mask_band
     - no
     - Mask band for the second dataset/variable
     -
     -
   * - var2_mask_value
     - no
     - Image mask value for the second dataset/variable
     -
     -
   * - var2_start_day
     - yes
     -
     -
     - 01
   * - var2_end_day
     - yes
     -
     -
     - 30
   * - var2_start_month
     - yes
     -
     -
     - 01
   * - var2_end_month
     - yes
     -
     -
     - 12
   * - start_year
     - yes
     -
     -
     - 2016
   * - end_year
     - yes
     -
     -
     - 2018
   * - var2_temporal_statistic
     - yes
     -
     -
     - mean
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json

.. _RST /timeseries/regression/feature_collection:

/timeseries/regression/feature_collection
*****************************************
| Performs regression analysis of the dataset variable summarized over a season for the features of an Earth Engine FeatureCollection.
| The values are averaged over the pixels lying within each feature of the feature collection.
| Permissions on the asset must be such that it is readable by anyone.
| Returns: json

Resource url example:

.. code-block::

    /timeseries/regression/feature_collection?dataset=LANDSAT7_TOA&variable=NDVI&temporal_statistic=Mean&var2_dataset=LANDSAT7_TOA&var2_variable=NDSI&var2_temporal_statistic=Mean&start_day=01&end_day=30&start_month=01&end_month=12&var2_start_day=01&var2_end_day=30&var2_start_month=01&var2_end_month=12&start_year=2016&end_year=2018&feature_collection_asset_id=USGS/WBD/2017/HUC08&sub_choices=["Animas"]&filter_by=name

.. list-table:: 
   :widths: 25 5 25 25 25
   :header-rows: 1

   * - NAME
     - REQUIRED
     - DESCRIPTION
     - DEFAULT
     - EXAMPLE
   * - feature_collection_asset_id
     - yes
     - EE FeatureCollection asset id, must have "Anyone can read" permissions
     -
     - USGS/WBD/2017/HUC08
   * - sub_choices
     - no
     - List of features to use in analysis, must be strings
     -
     - ["Animas"]
   * - filter_by
     - no
     - Property name to filter sub-choices
     -
     - name
   * - simplify_geometry
     - no
     - maxError in meters, see `ee.Feature.simplify <https://developers.google.com/earth-engine/apidocs/ee-feature-simplify>`_
     - None
     - 
   * - area_reducer
     - yes
     - Statistic over region
     - mean
     - mean, median, min, max
   * - dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     -
     -
     - NDVI
   * - temporal_statistic
     - yes
     -
     -
     - mean
   * - var2_dataset
     - yes
     -
     -
     - LANDSAT7_TOA
   * - variable
     - yes
     -
     -
     - NDSI
   * - temporal_statistic
     - yes
     -
     -
     - mean
   * - start_day
     - yes
     -
     -
     - 01
   * - end_day
     - yes
     -
     -
     - 30
   * - start_month
     - yes
     -
     -
     - 01
   * - end_month
     - yes
     -
     -
     - 12
   * - var2_start_day
     - yes
     -
     -
     - 01
   * - var2_end_day
     - yes
     -
     -
     - 30
   * - var2_start_month
     - yes
     -
     -
     - 01
   * - var2_end_month
     - yes
     -
     -
     - 12
   * - start_year
     - yes
     -
     -
     - 2016
   * - end_year
     - yes
     -
     -
     - 2018
   * - export_path
     - no
     - Export CSV results to a Google cloud storage bucket (must have correct permissions)
     -
     - climate-engine-public/my_csv_file.csv
   * - export_format
     - no
     - File format of export
     - json
     - csv, json


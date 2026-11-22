# Retire PRISM analysis sidecars

Stop creating separate dew-point CSVs and temperature-ordering logs. The 47,582-hillslope diagonal-intersection build produced two extra files per hillslope in each of its retained and published copies. Weather preparation and reporting consume the CLI. Security impact is low. Validation exercises the existing weather writers and compares generated model input with the prior production file. There is no new infrastructure or replacement analysis artifact.

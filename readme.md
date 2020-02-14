wepppy
=======

Wepppy is Python package for running WEPP (Water Erosion Prediction Project) and processing WEPP input and outputs.

### Installation
The wepppy repo is using Git LFS for some sqlite3 databases that are in the project. Pulling probably didn't download those correctly. So from the wepppy dir run the following to sync the database files:

```
> rm wepppy/climates/cligen/stations.db
> rm wepppy/climates/cligen/2015_stations.db
> rm wepppy/soils/ssurgo/data/statsgo/statsgo_spatial.db
> rm wepppy/soils/ssurgo/data/statsgo/statsgo_tabular.db
> rm wepppy/soils/ssurgo/data/surgo/surgo_tabular.db
> git lfs pull
```

### Copyright

University of Idaho 2015-Present

### Acknowledgements

This publication was made possible by the NSF Idaho EPSCoR Program and by the National Science Foundation under award 
number IIA-1301792.

### License

BSD-3 Clause (see license.txt)

wepppy
=======

Wepppy is Python package for running WEPP (Water Erosion Prediction Project) and processing WEPP input and outputs.


### Linux/Bash Installation
The wepppy repo is using Git LFS for some sqlite3 databases that are in the project. Pulling probably didn't download those correctly. So from the wepppy dir run the following to sync the database files:

```
> rm wepppy/climates/cligen/stations.db
> rm wepppy/climates/cligen/2015_stations.db
> rm wepppy/soils/ssurgo/data/statsgo/statsgo_spatial.db
> rm wepppy/soils/ssurgo/data/statsgo/statsgo_tabular.db
> rm wepppy/soils/ssurgo/data/surgo/surgo_tabular.db
> git lfs pull
```

### Docker
A docker base image is provided though wepppy, though wepppy works better on a bare metal linux install
https://github.com/rogerlew/wepppy-docker-base


### Windows

Clone repository using Github Client

Install Anaconda

Clone wepppy Anaconda environment

Create C:\geodata folder

Create C:\geodata\weppcloud_runs folder

Install Perl and make sure perl is added to path

Create wepppy.pth in C:\Users\roger\.conda\envs\wepppy\Lib\site-packages pointing to the directory where your wepppy repo is located.
e.g. "C:\Users\roger\.conda\envs\wepppy\Lib\site-packages\wepppy.pth" contains

```
C:\Users\roger\Documents\GitHub\wepppy\
```

copy rm.bat and ls.bat to C:\Windows

### Copyright

University of Idaho 2015-Present

### Acknowledgements

This publication was made possible by the NSF Idaho EPSCoR Program and by the National Science Foundation under award 
number IIA-1301792.

### License

BSD-3 Clause (see license.txt)

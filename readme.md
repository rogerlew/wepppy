wepppy
=======

Wepppy is Python package for running WEPP (Water Erosion Prediction Project) and processing WEPP input and outputs.


### Latest Release
[![DOI](https://zenodo.org/badge/125935882.svg)](https://zenodo.org/badge/latestdoi/125935882)

### Linux Installation

See [wepppy install with conda](https://github.com/rogerlew/wepppy/tree/master/install/conda)


### Docker

(has not been recently tested)

A docker base image is provided though wepppy, though wepppy works better on a bare metal linux install
https://github.com/rogerlew/wepppy-docker-base


### Windows

(has not been recently tested)

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

University of Idaho 2015-Present, Swansea Unveristy 2019-Present (Wildfire Ash Transport And Risk estimation tool, WATAR).

### Contributions

Roger Lew, Mariana Dobre, William Elliot, Pete Robichaud, Erin Brooks, Anurag Srivastava, Jim Frakenberger, Jonay Neris, Stefan Doerr, Cristina Santin, Mary E. Miller

### Acknowledgements

This publication was made possible by the NSF Idaho EPSCoR Program and by the National Science Foundation under award 
number IIA-1301792.

### License

BSD-3 Clause (see license.txt)

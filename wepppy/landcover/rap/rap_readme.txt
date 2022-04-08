http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-cover/v2/README

rangeland cover v2.0
====================
These data represent rangeland cover estimates described in Allred et al.
(2021).

Band 1 - annual forb and grass
Band 2 - bare ground
Band 3 - litter
Band 4 - perennial forb and grass
Band 5 - shrub
Band 6 - tree
Band 7 - annual forb and grass uncertainty
Band 8 - bare ground uncertainty
Band 9 - litter uncertainty
Band 10 - perennial forb and grass uncertainty
Band 11 - shrub uncertainty
Band 12 - tree uncertainty

No Data value = 65535
Uncertainty values are scaled by 100

Uncertainty values represent a standard deviation of predictions. As such, they
may be standardized by the mean when comparing across groups. Appropriate
actions should be taken when the mean is less than one.

Although these data were produced across a broad region, they are primarily
intended for rangeland ecosystems. Cover estimates may not be suitable in other
ecosystems, e.g., forests, agricultural lands.

Coordinate reference system
===========================
Data are in WGS84 Geographic Coordinate System (EPSG:4326); spatial resolution
is approximately 30m.

Google Earth Engine
===================
Data are available in the 'projects/rangeland-analysis-platform/vegetation-cover-v2'
ImageCollection.

Download tip
============
To download a specific location, use the GDAL virtual file system. For example,
the following gdal_translate command will retrieve a small section of Montana
(see the gdal_translate documentation for more information):

gdal_translate -co compress=lzw -co tiled=yes -co bigtiff=yes \
/vsicurl/http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-cover/v2/vegetation-cover-v2-2019.tif \
-projwin -108 48 -107 47 out.tif

Contacts
========
Brady Allred (allredbw@gmail.com)
Matthew Jones (matt.jones@ntsg.umt.edu)

Terms of use
============
This work is licensed under the Creative Commons Attribution-NonCommercial 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-nc/4.0/
Data are provided "as is" without warranty of any kind, express or implied.

Please attribute these data to:

Allred, B.W., B.T. Bestelmeyer, C.S. Boyd, C. Brown, K.W. Davies, M.C. Duniway,
L.M. Ellsworth, T.A. Erickson, S.D. Fuhlendorf, T.V. Griffiths, V. Jansen, M.O.
Jones, J. Karl, A. Knight, J.D. Maestas, J.J. Maynard, S.E. McCord, D.E. Naugle,
H.D. Starns, D. Twidwell, and D.R. Uden. 2021. Improving Landsat predictions of
rangeland fractional cover with multitask learning and uncertainty. Methods in
ecology and evolution. http://dx.doi.org/10.1111/2041-210x.13564

Changelog
========
2020-06-08 Public data release, version 2.0
2021-04-05 2020 cover estimates recalculated

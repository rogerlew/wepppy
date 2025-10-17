# Pure.css vendor fallback

The static asset build pipeline prefers copying Pure.css directly from `node_modules/purecss`.
If registry access is unavailable, drop `pure-min.css` and `grids-responsive-min.css` from an
official Pure.css release into this directory before running `build-static-assets.sh`. The
script will detect these local files and mirror them into `static/vendor/purecss/`.

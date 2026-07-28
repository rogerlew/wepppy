# DOM-04A Map Orchestration Field and Action Matrix

| Rendered identity/action | Controller behavior | Downstream boundary | Evidence |
| --- | --- | --- | --- |
| `#mapid` inside `#setloc_form` | Deck host and map status updates | Browser-only viewport | Actual render + existing map Jest |
| `#input_centerloc` | Parses `lon, lat[, zoom]`; Enter and Go navigate | Browser-only viewport | Actual render + existing map Jest |
| `[data-map-action="find-topaz"]` | Finds a TOPAZ ID and opens subcatchment drilldown | `report/sub_summary/<topaz_id>/` | Actual render + existing map Jest + report route test |
| `[data-map-action="find-wepp"]` | Finds a WEPP ID, resolves TOPAZ ID, and opens channel drilldown | `report/chn_summary/<topaz_id>/` | Actual render + existing map Jest + report route coverage |
| Deck hover coordinates | Posts numeric `{lat, lng}` to `url_for_run("elevationquery/")` and displays metres | elevation microservice | Focused map Jest + `tests/microservices/test_elevationquery.py` |
| `#drilldown`, `#mouseelev` | Receives returned HTML/elevation presentation | Browser-only presentation | Actual render + existing map Jest |

Excluded: basemap/layer/scale/legend/feature-modal behavior is DOM-04B. No
DOM-04A action persists map state or reaches RQ.

# Download failure-class assessment

Broken assumption: a server log or HTTP status alone is enough to diagnose a
failed download. The user needs a safe cause and support reference, and every
client stage must retain failure status. Search boundary: repository-owned browse,
files, manifests, shared authorization, dedicated download service and all three
bootstrap client entry points, including indirect Flask startup and error
translators. Unrelated HTTP applications and third-party clients are excluded.

| Consumer / dependency | Disposition | Regression evidence |
| --- | --- | --- |
| Required secrets -> lazy owner lookup -> Flask startup | Confirmed defect repaired: typed RuntimeError-compatible configuration error | Real lazy Flask HTTP/client probe; missing, empty, unreadable and malformed UTF-8 tests; setting/reason shown, no secret path |
| Browse manifest and direct file download | Confirmed defect repaired: safe JSON and response/log request ID | Parameterized actual route tests; original SECRET_KEY failure reaches real client parser |
| Browser HTML errors and files API | Confirmed defect repaired: safe cause/reference; known JWT configuration cause preserved | HTML/JSON route tests, explicit debug opt-in preserved |
| JWT and group browse/schema/download/D-Tale/GDAL | Confirmed defect repaired: authored recovery message survives all auth translators | Run and twelve group-route JWT configuration tests; ordinary auth rejection and successful delivery retained |
| Dedicated archive service | Confirmed defect repaired: application exception handlers | Known/unexpected failure tests plus existing byte/range/HEAD/auth tests |
| NoDir compatibility translators (browse, files, download, D-Tale, GDAL) | Confirmed change-induced regression repaired: retain 500/503 codes without private error text | Ten translator/HTTP regressions, NODIR_INVALID_ARCHIVE and NODIR_LOCKED |
| D-Tale upstream exception text | Confirmed exposure repaired: upstream 5xx becomes safe correlated response | Upstream detail redaction test, D-Tale focused suite, independent security probe |
| Deliberately authored ERMiT/D-Tale operational errors | Preserved explicit messages | PublicHTTPException classification; focused download/D-Tale suite |
| Windows and shell aria wrappers | Confirmed defect repaired: shared Python HTTP reporting, no continuation after bad manifest | Local HTTP tests, native batch full success/failure and exit propagation; Linux entry and real aria |
| aria2c payload failure | Confirmed defect repaired: bounded failed-URL diagnostic request; original nonzero exit retained | Real Linux/Windows aria; saved-session trailing TAB, spaces and Unicode URLs |
| Legacy Python archive client | Confirmed defect repaired: HTTP body reporting and interrupted-read handling before file write | Real local HTTP 500 and truncated stream CLI failures; successful ZIP and extracted bytes |
| Reverse-proxy-generated errors / post-header stream interruption | Bounded handling, not newly deployed | Client plain/large body and interrupted-read tests; no new JSON status possible after headers |

Preserved valid states: absent user JWT still permits public access; private and
nonowner rejection remains; exact successful file/archive bytes; genuinely empty
HTTP 200/comment-only manifests; existing CLI arguments, 10-way transfer setting
and resume behavior. A login/error document or orphan option cannot masquerade
as an empty project. Explicit external manifest origins remain supported; HTTP
redirects do not forward Authorization to a different origin.

Prior repair: `20261027_service_secret_dependency_audit` corrected provisioning
but did not certify client-visible failure behavior. Prior dedicated-download and
filesystem-transparency packages supply the existing boundaries. No new secret,
service, permission, authorization bypass or scientific parameterization is added.

Remaining rollout scope: production installation/restart and an ordinary-user
smoke on the deployed revision. No production configuration was broken to create
a test failure. This assessment does not certify all HTTP errors in WEPPcloud.

Transitive sweep followed browse.create_app registrations, including sibling `_gdalinfo.py`, report delegation and flow use of the main translator. Report already uses the corrected auth helper; grouped GDAL and D-Tale needed the same explicit conversion. Query-engine feature_access imports BrowseAuthError but uses its own explicit-detail/traceback handler, so the new browse boundary does not mask that service. Its separate privacy/error contract is outside this download repair and is not certified here.

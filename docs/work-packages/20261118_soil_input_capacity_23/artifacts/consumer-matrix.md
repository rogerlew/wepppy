# Soil input capacity consumer assessment

Broken assumption: all native input horizons share the ten-layer calculation
limit. The selected executable now owns input capacity; calculation storage is
unchanged. Standalone calls default to ten unless explicitly given capacity.

| Consumer | Disposition | Evidence |
| --- | --- | --- |
| SSURGO/STATSGO raw writers, all collection build routes | Forward selected capacity through collection and individual serializers, including special water/urban branches | Real Puaulu 7778/2006 writer tests; 21 serialized records |
| SSURGO fallback donor materialization | Forward selected capacity to individual donor write | Call-site inventory in core/soils.py |
| General soil utility and prepared hillslopes | Store capacity in utility and append to process task tuples | Real Puaulu Disturbed-to-preparation test |
| Multi-OFE and Disturbed worker generation | Forward through process dictionaries and synthesis | Two OFEs each retain 21 Puaulu horizons |
| Channel soil writers | Use selected capacity during normalization | Direct writer boundary tests; real watershed replay |
| Final hillslope, batch hillslope, flowpath, watershed, batch watershed launch | Inspect referenced soil inputs before native invocation, without rewriting | Real files and capability downgrade test |
| Uploaded soil preparation | Retain admitted format and existing preservation path; execution guard checks capacity only | Upload preservation and validation-only tests |
| Treatment soil derivatives | Forward selected capacity through both summary and fallback source reads | Real Puaulu 7778/9002 treatment regression |
| General/Lake Tahoe location derivatives | Forward selected capacity to the active shared modifier | Real Puaulu location writer regression |
| AgFields Concept1/hybrid parent synthesis | Forward selected AgFields executable capacity to multi-OFE synthesis | Real Puaulu two-OFE synthesis and integration tests |
| General-location restrictive-conductivity modifier | Forward selected capacity; restrictive conductivity change retains all horizons | Real Puaulu restrictive-conductivity regression |
| Roads soil assemblers | Existing owned one-horizon-per-OFE templates; no SSURGO profile forwarding | Four builders in mods/roads/_soil_inputs.py; retain ten default |
| Standalone soil_specialization helper | No active production caller found; retain explicit bounded API | Search found only commented historical call |
| ISRIC/SIFT/EU/AU dataset writers | Separate bounded sources; retain legacy ten default | No confirmed 11+ input consumer in incident path |
| Builder capability graph and executable selection revision | Preserve historical ten-capacity identity; bind non-ten capacity to provider freshness | Capability identity boundary tests; real replay exposed and closed validator mismatch |

Evidence does not establish future datasets can never exceed 23. Excess remains
an explicit error. Windows artifacts are outside this Linux release scope.

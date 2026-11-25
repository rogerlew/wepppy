# Roads retry recovery checkpoint

Base 66fdcc5cc. The operator requested a more reliable, gentle retry with observable timeouts. Forest returned upstream_timeout after one 20-second attempt, reference fe8fc2bbbc084600ade3f505a1d190cd. The existing per-request budget prevents a full second attempt after timeout. The amended Roads OSM contract, section “Recovery across completed requests”, permits bounded browser backoff using the same authorized POST. Conformance pending. This changes recovery timing only. Legacy API clients retain their behavior. There is no new external provider, datastore, project mutation, or model parameterization.

Test initial and legacy responses, successful nonempty and empty results, repeated timeout, HTTP overload and Retry-After, malformed and access errors, exhausted time and attempt budgets, and project form replacement. Keep existing response byte, authorization and CSRF checks on each request. Review the rendered status and exercise the real Fetch action.

Independent correctness/UX and security reviewers accepted the revised contract. Both flagged unobservable internal attempts in successful responses. Report previously observed failed attempts on recovery and reserve both possible upstream attempts before resubmitting. Both accepted explicit retry eligibility and safe termination on legacy responses.

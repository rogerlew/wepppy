There are 3 deployments of this docker app.

## development
- host: forest.bearhive.internal 
- domain: wc.bearhive.duckdns.org
- docker-compose.dev.yml

## test production
- host: forest1.bearhive.internal 
- domain: wc-prod.bearhive.duckdns.org
- docker-compose.prod.yml

## production
- host: wepp1
- domain: wepp.cloud

## Notes for Next Pass
- Static assets now build via `wctl build-static-assets`; re-run before image rebuilds so `controllers.js` and vendor bundles stay current.
- Kubernetes migration is still pending. When that work resumes, plan on duplicating the static build stage so the proxy image (or init container) ships with the same `/weppcloud/static` tree baked in—no shared volumes required.

# Docker CLI component qualification

The production and development Dockerfiles select the upstream Docker CLI 29.10.0 archive. The build checks its published SHA-256, `94e8261e6e566c719973a81b22906d7b0a2655440b83fca0ea9c26215437541a`, before extracting the client. The installed binary was readable and executable by UID 1002, GID 130, and its SHA-256 was `df7684b939d373a90a6bc4e8b8a2a1f131831fa260aff1afc0a01a1fa3f44171`. The larger engine archive contains a different client build. All qualification here uses the CLI-only archive. [Docker distribution](https://download.docker.com/linux/static/stable/x86_64/)

Read-only version requests from this binary negotiated API 1.54 on wepp1 and wepp2, and 1.55 on wepp3. A disposable renderer on forest accepted the client’s real DEVAL render request over standard input. The output contained the fixture run ID and 14,076,835 bytes of HTML, owned by 1002:130 with mode 0644. Its SHA-256 was `259a9fe8d75628d45acc4287b7ad90038d49d7f190f8a86c89b0302459c6ad9e`.

Component evidence is retained on forest under `grype-remediation-20261123/round2/`, including the published checksum, the image-layer build, host negotiation records and `docker-render.log`.

# Setuptools vendor repair

The production and development requirements now select setuptools 80.10.2. In a trial layer on the reviewed common image, installed private metadata under `setuptools/_vendor` identified jaraco.context 6.1.0 and wheel 0.46.3. Their respective Grype fix thresholds were 6.1.0 and 0.46.2. Both old copies were removed during package installation.

The production run-ID generator loaded its real packaged word lists and generated IDs with both configured email prefixes under UID 1002 and GID 130. PyFilesystem wrote and read a file through its registered memory opener. The setuptools backend built a wheel whose module bytes matched the source. Both the base and trial passed the installed Python dependency check. The trial emitted a packaging-version warning about optional license expression validation.

The upstream 84.2.1 wheel removes `pkg_resources`. The same run-ID import against that wheel failed in `awesome_codename.data`. Version 80.10.2 repairs both vendored components while retaining that interface. Three PyPI advisory identifiers against setuptools itself apply to both 78.1.1 and 80.10.2. These remain open pending consumer migration or a compatible upstream fix. [Setuptools releases](https://setuptools.pypa.io/en/latest/history.html)

Protected trial evidence on forest is under `grype-remediation-20261123/round2/` in the deployment dependency-security evidence store. It includes wheel files checked against PyPI SHA-256, separate import results for both versions and `setuptools-consumers.log`.

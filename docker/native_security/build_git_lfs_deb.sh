#!/bin/sh
# Build the upstream Debian package with the dependency revisions qualified for WEPPcloud.
set -eu
cd /build
git clone --depth=1 --branch v3.8.1 https://github.com/git-lfs/git-lfs.git src
cd src
test "$(git rev-parse HEAD)" = a662a6dbfedf706cfa9fc7a5b7bcc7ba2e2c8a65
export GOTOOLCHAIN=local
go mod edit -go=1.26.0 \
    -require=github.com/klauspost/compress@v1.20.2 \
    -require=golang.org/x/crypto@v0.59.0 \
    -require=golang.org/x/net@v0.62.0 \
    -require=golang.org/x/sync@v0.25.0 \
    -require=golang.org/x/sys@v0.50.0 \
    -require=golang.org/x/text@v0.44.0
go mod download github.com/klauspost/compress golang.org/x/crypto golang.org/x/net \
    golang.org/x/sync golang.org/x/sys golang.org/x/text
sha256sum -c - <<'CHECKSUMS'
88e99bd80705e6e4a36625144ae4cdaa7f5997eb4f4907c52df7d23966b3ffc3  go.mod
9e1c0a02811febad53aeee37d0871863264426d8efc7e79b7f9da0f23ae83dff  go.sum
CHECKSUMS
go mod vendor

# Give the local binary its own package revision and retain upstream history.
cat > /tmp/wepp-changelog <<'CHANGELOG'
git-lfs (3.8.1+wepp1) unstable; urgency=medium

  * Build with Go 1.26.11 and the reviewed compression, crypto and network dependencies.

 -- WEPPpy project <rogerlew@users.noreply.github.com>  Mon, 23 Nov 2026 14:40:00 +0000

CHANGELOG
cat debian/changelog >> /tmp/wepp-changelog
mv /tmp/wepp-changelog debian/changelog
test "$(dpkg-parsechangelog -SVersion)" = 3.8.1+wepp1
FORCE_LOCALIZE=true DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -b -us -uc -d
mkdir -p /out
mv ../git-lfs_3.8.1+wepp1_amd64.deb /out/git-lfs.deb

#!/usr/bin/env bash
#
# scripts/vendor_js9.sh
#
# Download, build, and install the JS9 FITS viewer web files into the Django
# static directory (or a custom target path).
#
# WHY VENDORED:
#   JS9 cannot be reliably loaded from the js9.si.edu CDN because:
#     1. Web Workers (js9worker.js) are hard-blocked by browsers when the script
#        is not served from the same origin as the page — there is no CORS
#        workaround for this browser security restriction.
#     2. The WebAssembly file (astroemw.wasm) is fetched at runtime, and
#        js9.si.edu does not serve it with an Access-Control-Allow-Origin header.
#   Serving JS9 from the same origin as the web application avoids both issues.
#
# HOW TO UPDATE:
#   1. Change JS9_VERSION below to the desired release tag, e.g. "v3.9".
#      Releases: https://github.com/ericmandel/js9/releases
#      NOTE: The JS9 repository was archived in December 2024; v3.9 is the
#      final release and no newer versions are expected.
#   2. Re-run this script locally:
#        bash scripts/vendor_js9.sh
#      OR rebuild the Docker image (which runs this script automatically):
#        docker compose build web
#
# USAGE:
#   bash scripts/vendor_js9.sh [target_dir]
#
#   target_dir  Directory to install JS9 web files into.
#               Default: ywangvaster_webapp/static/vendored/js9
#               In Docker the Dockerfile passes /opt/js9_static as the target.

set -euo pipefail

JS9_VERSION="v3.9"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TARGET="${SCRIPT_DIR}/../ywangvaster_webapp/static/vendored/js9"
TARGET_DIR="${1:-${DEFAULT_TARGET}}"
TARGET_DIR="$(realpath -m "${TARGET_DIR}")"

echo "==> Installing JS9 ${JS9_VERSION} to ${TARGET_DIR}"

BUILD_TMP="$(mktemp -d)"
trap 'rm -rf "${BUILD_TMP}"' EXIT

echo "==> Downloading JS9 source tarball ..."
wget -q \
    "https://github.com/ericmandel/js9/archive/refs/tags/${JS9_VERSION}.tar.gz" \
    -O "${BUILD_TMP}/js9.tar.gz"

tar -xzf "${BUILD_TMP}/js9.tar.gz" -C "${BUILD_TMP}"

# GitHub strips the leading 'v' from the directory name in the tarball
SRC_DIR="${BUILD_TMP}/js9-${JS9_VERSION#v}"

echo "==> Running configure + make + make install ..."
mkdir -p "${TARGET_DIR}"
cd "${SRC_DIR}"
./configure --with-webdir="${TARGET_DIR}"
make
make install

echo "==> JS9 ${JS9_VERSION} successfully installed to ${TARGET_DIR}"

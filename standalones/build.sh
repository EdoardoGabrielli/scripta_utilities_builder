#!/usr/bin/env bash
# Build move_anomalie as a standalone binary for macOS / Linux.
# Requires: pip install pyinstaller  (see requirements-build.txt)
#
# Output: dist/move_anomalie

set -euo pipefail
cd "$(dirname "$0")"

pyinstaller move_anomalie.spec \
    --distpath dist \
    --workpath build/work \
    --noconfirm

echo ""
echo "Build complete: dist/move_anomalie"
echo "Copy dist/move_anomalie + anomalie.txt into the images folder and run it."

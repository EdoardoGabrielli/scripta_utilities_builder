#!/usr/bin/env bash
# Smoke test for the macOS/Linux binary.
# Usage: bash smoke_test.sh <path-to-binary>
# Example: bash smoke_test.sh dist/move_anomalie

set -euo pipefail
"${1:?Usage: smoke_test.sh <path-to-binary>}" --smoke

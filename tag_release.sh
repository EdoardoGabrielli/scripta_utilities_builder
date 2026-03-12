#!/usr/bin/env bash
set -euo pipefail

TAG="v1.0.0"

git tag -d "$TAG" 2>/dev/null || true
git push origin ":refs/tags/$TAG" 2>/dev/null || true

git tag "$TAG"
git push origin "$TAG"

echo "Tag $TAG pushed."

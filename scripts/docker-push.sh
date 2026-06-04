#!/usr/bin/env bash
# Build and push app + proxy tags. Requires DOCKER_IMAGE (repo path without tag).
# Example: export DOCKER_IMAGE=mycompany/brazos-gmps-app
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${DOCKER_IMAGE:?Set DOCKER_IMAGE (e.g. mycompany/brazos-gmps-app)}"
TAG_SUFFIX="${1:-latest}"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running."
  exit 1
fi

echo "Building ${IMAGE}:app-${TAG_SUFFIX} and :proxy-${TAG_SUFFIX} ..."
docker build -t "${IMAGE}:app-${TAG_SUFFIX}" .
docker build -t "${IMAGE}:proxy-${TAG_SUFFIX}" ./proxy

echo "Pushing ..."
docker push "${IMAGE}:app-${TAG_SUFFIX}"
docker push "${IMAGE}:proxy-${TAG_SUFFIX}"

echo ""
echo "Published:"
echo "  ${IMAGE}:app-${TAG_SUFFIX}"
echo "  ${IMAGE}:proxy-${TAG_SUFFIX}"

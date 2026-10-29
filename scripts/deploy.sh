#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:-$(git rev-parse --short HEAD)}"
export APP_VERSION="$VERSION"
export APP_IMAGE="apex-ops-api:$VERSION"
echo "Building release $APP_IMAGE"
docker build --tag "$APP_IMAGE" .
# Compose reads APP_IMAGE and runs the exact versioned image.
docker compose up -d --no-build --remove-orphans
printf '%s\n' "$APP_IMAGE" > .last_deployed_image
echo "Waiting for readiness..."
for _ in $(seq 1 30); do
  if curl --fail --silent http://localhost:"${API_PORT:-8080}"/ready >/dev/null; then
    echo "Release $VERSION is ready"
    exit 0
  fi
  sleep 2
done
echo "Release did not become ready. Inspect: docker compose logs --tail=100 api" >&2
exit 1

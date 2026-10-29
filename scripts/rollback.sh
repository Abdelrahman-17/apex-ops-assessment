#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <known-good-image-tag> (example: $0 apex-ops-api:abc1234)" >&2
  echo "List local releases with: docker images apex-ops-api" >&2
  exit 2
fi
if ! docker image inspect "$TARGET" >/dev/null 2>&1; then
  echo "Image not found locally: $TARGET" >&2
  exit 2
fi
export APP_IMAGE="$TARGET"
export APP_VERSION="rollback-$(date -u +%Y%m%dT%H%M%SZ)"
docker compose up -d --no-build --remove-orphans
for _ in $(seq 1 30); do
  if curl --fail --silent http://localhost:"${API_PORT:-8080}"/ready >/dev/null; then
    echo "Rollback successful: running $TARGET"
    exit 0
  fi
  sleep 2
done
echo "Rollback target did not become ready; inspect docker compose logs api" >&2
exit 1

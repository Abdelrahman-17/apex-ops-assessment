# Operations Runbook

## Deploy
1. Confirm Docker Desktop/Engine is healthy: `docker info` and `docker compose version`.
2. Run `./scripts/deploy.sh <unique-tag>` (for example `v1`).
3. Verify `docker compose ps`, `curl -fsS localhost:8080/health`, and `curl -fsS localhost:8080/ready`.
4. Confirm logs: `docker compose logs --tail=100 api`.

## Roll back
1. Identify a known-good local image: `docker images apex-ops-api`.
2. Run `./scripts/rollback.sh apex-ops-api:<known-good-tag>`.
3. Verify `/ready`, API smoke test, and logs. If rollback does not become ready, inspect logs and return to the last known-good tag.
4. Keep the persistent data volume unless a data reset is explicitly intended.

## Incident response
1. Confirm symptom and time; capture status, request ID, and relevant logs.
2. Check container state: `docker compose ps`.
3. Check readiness and metrics: `curl -i localhost:8080/ready` and `curl -s localhost:8080/metrics`.
4. Inspect recent logs: `docker compose logs --since=10m --tail=200 api`.
5. If the service is unhealthy after a release, roll back to a known-good image and verify readiness.
6. Record impact, timeline, suspected cause, recovery, and follow-up actions. Do not include secrets or personal data.

## Troubleshooting
- Port already in use: set `API_PORT=8081` in `.env`, then recreate with `docker compose up -d`.
- Image missing during rollback: rebuild the old commit/tag or use a known-good image available locally.
- Readiness fails: check SQLite volume permissions and `docker compose logs api`.
- Container exits: inspect `docker compose ps -a` and logs; check configuration without printing secret values.
- Reset demo data only if safe: `docker compose down -v` permanently removes the named volume data.

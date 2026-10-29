# Decision Memo

## Scope
Deliver a local-first operations API that can be built, tested, run, inspected, and rolled back without production credentials or paid cloud resources.

## Decisions and trade-offs
- **Flask + Gunicorn:** small Python service with a simple production WSGI server. It is intentionally not a full business platform.
- **SQLite + named volume:** removes the need for a second service and demonstrates persistence locally. It is not suitable for horizontally scaled production writes; use managed PostgreSQL for that case.
- **Docker Compose:** gives reviewers a reproducible single-host deployment. Kubernetes is deliberately out of scope for this small assessment.
- **Versioned local images:** enables deterministic local rollback without relying on a mutable `latest` tag. Production would use an authenticated registry and immutable digests.
- **Readiness, JSON logs, metrics:** supports basic diagnosis at low operational cost. Metrics are process-local counters and reset when the process restarts; a production service should scrape/store them externally.
- **CI gates:** lint, automated tests, intentional negative-test verification, image build, and vulnerability scan. No automatic production deployment is configured.

## Risks / next steps
Add authentication/authorization, rate limiting, database migrations, structured error taxonomy, richer tests, dependency-update automation, SBOM/signing, registry-based releases, external metrics/log storage, backup/restore drills, and TLS before any internet-facing deployment.

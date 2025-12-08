# STEPS.md
# Progress tracker for Option ARO clone. Each step is updated to ✅ when created.

## Phase 1: Core Infrastructure & Minimal E2E Demo

1. [✅] bootstrap: create repo structure, README skeleton, LICENSE, .gitignore, STEPS.md
   - outputs: README.md, .gitignore, LICENSE, STEPS.md
   - commit: chore(repo): bootstrap repo scaffold

2. [🔄] docker-compose: redis, mongo, feed-generator, worker, socket-gateway, api-gateway, auth, storage, analytics, logging
   - outputs: docker-compose.yml
   - commit: feat(dev): docker-compose for local demo

3. [❌] service: feed-generator (realistic dummy data with products, expiries, strikes, quotes, chains)
   - outputs: services/feed-generator/
   - commit: feat(feed): add realistic feed generator

4. [❌] service: worker-enricher (Celery) compute iv/straddle/pcr/store/publish
   - outputs: services/worker-enricher/
   - commit: feat(worker): add enrichment worker and tasks

5. [❌] service: socket-gateway (Flask-SocketIO) + redis pubsub listener
   - outputs: services/socket-gateway/
   - commit: feat(socket): implement socket gateway and redis listener

6. [❌] service: storage (MongoDB wrapper service)
   - outputs: services/storage/
   - commit: feat(storage): add mongodb storage service

7. [❌] basic end-to-end demo (ingest->worker->store->socket->client test)
   - outputs: small demo working; instructions in README
   - commit: feat(demo): add minimal e2e demo

## Phase 2: Complete Backend Microservices

8. [❌] service: auth (JWT) with login/register + user store
   - outputs: services/auth/
   - commit: feat(auth): add auth endpoints

9. [❌] service: api-gateway (Flask) with REST endpoints + OpenAPI
   - outputs: services/api-gateway/
   - commit: feat(api): add api-gateway with openapi

10. [❌] service: analytics (aggregation, PCR, IV surface, OHLC)
    - outputs: services/analytics/
    - commit: feat(analytics): add analytics aggregation service

11. [❌] service: logging-service (structured logs ingestion)
    - outputs: services/logging-service/
    - commit: feat(logging): add logging consumer and doc

12. [❌] scripts: start-local.sh, stop-local.sh, seed-data.sh, subscribe-example.js
    - outputs: scripts/
    - commit: chore(scripts): add utility scripts

## Phase 3: Production Readiness

13. [❌] kubernetes manifests (deployment + service + configmap for each service)
    - outputs: k8s/
    - commit: feat(k8s): add kubernetes manifests

14. [❌] tests: unit tests for core logic + integration test
    - outputs: tests/
    - commit: test: add unit and integration tests

15. [❌] CI: GitHub Actions (lint, test, build docker images)
    - outputs: .github/workflows/
    - commit: ci: add github actions workflow

16. [❌] observability: prometheus configs + grafana dashboards
    - outputs: observability/
    - commit: chore(obs): add prometheus & grafana examples

17. [❌] examples: curl commands, Postman collection, sample outputs
    - outputs: examples/
    - commit: docs(examples): add api examples

18. [❌] documentation: complete README.md with architecture, quickstart, how-to-run
    - outputs: README.md updates
    - commit: docs: complete main README

19. [❌] documentation: VERIFICATION.md with test procedures
    - outputs: VERIFICATION.md
    - commit: docs: add verification guide

20. [❌] final polish: CODE_OF_CONDUCT.md, env.example files, service READMEs
    - outputs: various documentation files
    - commit: docs: final documentation polish

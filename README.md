# Resilience PoC

This repository is a proof-of-concept event-driven resilience system for CI/CD pipelines. It contains small services that together simulate pipeline failures, detect and classify dependency failures, make remediation decisions based on rule sets, and execute (simulated) remediation actions.

Contents
- Overview: components and how they interact
- How the PoC works: deterministic failure -> decision -> remediation path
- Files: map of important code and config files
- Run locally: how to start the stack and trigger the webhook
- Develop & test: how to make changes and run unit / integration tests
- CI / Jenkins: how CI is configured and what the pipeline does
- Troubleshooting: common issues and checks

Architecture overview
- `pipeline_simulator` produces CI/CD events (exchange `cicd`) and exposes an HTTP webhook for on-demand events.
- `observability` normalizes pipeline events into the internal `resilience` exchange.
- `failure_detector` evaluates observability events and emits `failure.detected` events.
- `failure_classifier` classifies failures and emits `failure.classified`.
- `decision_engine` fetches rules from the rules manager and publishes `remediation.command` decisions.
- `failure_solver` consumes `remediation.command`, executes remediation (simulated), stores results in Postgres (`remediation_actions`), and publishes `remediation.result`.

How the PoC works (deterministic path)
1. You trigger one failed pipeline run with `POST /simulate` in `pipeline_simulator`.
2. `observability` transforms the event into the `resilience` exchange.
3. `failure_detector` emits a `failure.detected` event for dependency-stage failures.
4. `failure_classifier` maps the error text to a deterministic category/severity.
5. `decision_engine` loads rules from `rules_manager` and selects the remediation action.
6. `failure_solver` executes the selected action handler and emits `remediation.result`.
7. `failure_solver` also persists the result in Postgres (`remediation_actions`).

Deterministic mapping used in the demo
- Timeout-like errors -> category `Timeout` -> action `increase_timeout_and_retry`
- Connection reset/hang errors -> category `Connection lost` -> action `change_mirror_and_retry`
- 404/not found errors -> category `404` -> action `validate_dependency_and_fallback`
- Hash/checksum errors -> category `Checksum mismatch` -> action `clean_cache_and_retry`

Important files
- `docker-compose.yml` — service orchestration for local runs
- `pipeline_simulator/app.py` — simulator + HTTP webhook (`/simulate`, `/health`)
- `rules_manager/app.py` — FastAPI service exposing `/rules` and `/health`
- `failure_detector/app.py`, `failure_classifier/app.py`, `decision_engine/app.py`, `failure_solver/app.py` — service entrypoints
- `common/` — shared helpers (config, logging, messaging)
- `tests/` — pytest tests and fixtures
- `.github/workflows/ci.yml` — GitHub Actions workflow for CI
- `Jenkinsfile` — Jenkins pipeline (mirror of CI workflow)

Quick start (recommended)
1. Install Docker and Docker Compose (Docker Desktop on Windows).
2. From the repository root, start the stack:

```powershell
docker compose up -d
```

3. Check the pipeline simulator health endpoint:

```powershell
curl http://localhost:8001/health
```

4. Trigger a single simulated failed pipeline event (webhook):

```powershell
curl -X POST http://localhost:8001/simulate \
  -H "Content-Type: application/json" \
  -d '{"status":"failed","dependency":"requests","version":"2.31.0","error":"ReadTimeoutError: HTTPSConnectionPool(host=''pypi.org'', port=443): Read timed out."}'
```

You can use the `error` field to force a specific recovery path. For example, a timeout-style error should flow to the `increase_timeout_and_retry` remediation rule.

5. Verify remediation persistence in Postgres (example):

```powershell
docker exec postgres psql -U resilience_user -d resilience -c "SELECT * FROM remediation_actions ORDER BY created_at DESC LIMIT 5;"
```

Run the deterministic PoC flow (recommended for demos)
1. Start from a clean state.

```powershell
docker compose down -v
```

2. Start the stack with periodic simulation disabled so only your manual trigger is processed.

```powershell
$env:SIMULATOR_DISABLE_LOOP="true"
docker compose up -d
```

3. Trigger one known failure path (timeout -> increase_timeout_and_retry).

```powershell
curl -X POST http://localhost:8001/simulate \
  -H "Content-Type: application/json" \
  -d '{"status":"failed","dependency":"requests","version":"2.31.0","error":"ReadTimeoutError: HTTPSConnectionPool(host=''pypi.org'', port=443): Read timed out."}'
```

4. Verify solver persistence for the selected action.

```powershell
docker exec postgres psql -U resilience_user -d resilience -c "SELECT action, status, details->>'pipeline_id' AS pipeline_id, created_at FROM remediation_actions ORDER BY created_at DESC LIMIT 5;"
```

Analyze PoC execution
- Check action selection in the decision engine logs:

```powershell
docker compose logs decision_engine --tail=100
```

- Check action execution in the failure solver logs:

```powershell
docker compose logs failure_solver --tail=100
```

- Confirm end-to-end delivery with a strict SQL check for timeout recovery:

```powershell
docker exec postgres psql -U resilience_user -d resilience -c "SELECT count(*) AS timeout_recoveries FROM remediation_actions WHERE action = 'increase_timeout_and_retry' AND status = 'success';"
```

Run only selected services (faster iteration)
 - To run only the services needed to test the webhook → observability → detector → classifier → decision → solver flow, bring up: `rabbitmq`, `postgres`, `rules_manager`, `observability`, `failure_detector`, `failure_classifier`, `decision_engine`, `failure_solver`, `pipeline_simulator`.
 - Example:

```powershell
docker compose up -d rabbitmq postgres rules_manager observability failure_detector failure_classifier decision_engine failure_solver pipeline_simulator
```

Development and tests
- Python packages for tests are listed in `requirements-test.txt`.

Test environment setup (local)
```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-test.txt
```

Run focused unit tests (fast):

```powershell
.\.venv\Scripts\python -m pytest -q tests/test_failure_solver_action.py
```

Run webhook and recovery-flow tests (no Docker):

```powershell
.\.venv\Scripts\python -m pytest -q tests/test_pipeline_simulator_webhook.py tests/test_poc_recovery_flow.py
```

Run complete local test suite:

```powershell
.\.venv\Scripts\python -m pytest -q tests
```

How to analyze test results
- `tests/test_pipeline_simulator_webhook.py`: validates webhook payload override and event publishing shape.
- `tests/test_poc_recovery_flow.py`: validates deterministic chain (error text -> classification -> rule decision -> solver outcome).
- `tests/test_failure_solver_action.py`: validates concrete action handlers (`retry`, `clean_cache`, `dependency_substitution`) and unknown-action fallback.
- If tests fail, rerun with verbose output and stop at first failure:

```powershell
.\.venv\Scripts\python -m pytest -vv -x tests
```

- For failures involving running services, correlate pytest output with container logs:

```powershell
docker compose logs --tail=200 decision_engine failure_solver pipeline_simulator
```

Full end-to-end integration checks require Docker Compose up and are executed by CI/Jenkins (webhook trigger + Postgres remediation validation).

Making changes
- Add or modify rules: edit `rules_manager/rules.json` or use the API at `/rules` (see `rules_manager/app.py`).
- Add new tests under `tests/` and run them locally.
- When adding Python package dependencies for a service, update that service's `requirements.txt` and rebuild the image:

```powershell
docker compose build pipeline_simulator
docker compose up -d pipeline_simulator
```

CI and Jenkins
- GitHub Actions: see [.github/workflows/ci.yml](.github/workflows/ci.yml). The workflow starts the compose stack with the simulator loop disabled, waits for the simulator, runs pytest, triggers the timeout failure webhook, and verifies the `increase_timeout_and_retry` remediation row in Postgres.
- Jenkins: see `Jenkinsfile` which mirrors the CI steps for Jenkins pipelines.

Environment variables (not exhaustive)
- `SIMULATOR_HTTP_PORT` (default `8001`) — pipeline simulator HTTP port
- `SIMULATOR_DISABLE_LOOP` (true/false) — disables the periodic emitter when testing
- RabbitMQ/Postgres/Elasticsearch connection env vars are set in `docker-compose.yml` and consumed by `common/config/settings.py`.

Troubleshooting
- If services fail to start, inspect logs:

```powershell
docker compose logs --tail=200
docker compose logs failure_solver
```

- If the simulator `/health` endpoint is not reachable, ensure the container port is exposed (`8001:8001`) and that the simulator process started without errors (`docker compose logs pipeline_simulator`).
- If remediation rows are not appearing, check that `failure_solver` container can reach `postgres` and `rabbitmq` and inspect `failure_solver` logs for errors.

Next steps and suggestions
- Add more integration tests using `testcontainers` or in-container pytest runs to validate the end-to-end path in CI without depending on a full machine environment.
- Optionally add automated image build/publish steps in CI to push images to a registry.

---
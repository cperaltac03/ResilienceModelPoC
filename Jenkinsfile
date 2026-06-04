pipeline {
  agent any

  stages {
    // Pull the repository configured for this Jenkins job.
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    // Ensure a recent pip is available before installing test dependencies.
    stage('Setup Python') {
      steps {
        sh 'python3 -m pip install --upgrade pip'
      }
    }

    // Install shared test dependencies used by unit and integration checks.
    stage('Install dependencies') {
      steps {
        sh 'pip install -r requirements-test.txt'
      }
    }

    // Start the complete PoC stack; disable periodic simulation for deterministic runs.
    stage('Start Docker Compose') {
      steps {
        sh 'SIMULATOR_DISABLE_LOOP=true docker compose up -d'
      }
    }

    // Gate the pipeline until the simulator API is reachable.
    stage('Wait for simulator') {
      steps {
        sh '''
          python3 - <<'PY'
          import time
          import requests

          for _ in range(30):
              try:
                  r = requests.get('http://localhost:8001/health', timeout=5)
                  if r.status_code == 200:
                      print('Simulator ready')
                      break
              except Exception:
                  pass
              time.sleep(2)
          else:
              raise SystemExit('Simulator endpoint not available')
          PY
        '''
      }
    }

    // Execute repository test suite before running the end-to-end webhook check.
    stage('Run tests') {
      steps {
        sh 'pytest tests'
      }
    }

    // Trigger a deterministic timeout failure and assert remediation persistence in Postgres.
    stage('Trigger webhook and validate') {
      steps {
        sh '''
          # Trigger one failed pipeline event with timeout-like error text.
          response=$(curl -sS -X POST http://localhost:8001/simulate \
            -H "Content-Type: application/json" \
            -d '{"status":"failed","dependency":"requests","version":"2.31.0","error":"ReadTimeoutError: HTTPSConnectionPool(host=''pypi.org'', port=443): Read timed out."}')

          pipeline_id=$(echo "$response" | python3 -c 'import sys,json; print(json.load(sys.stdin)["event"]["pipeline_id"])')
          echo "Triggered pipeline_id: $pipeline_id"

          # Poll for the expected remediation action selected by the decision engine.
          for i in $(seq 1 20); do
            row_count=$(docker exec postgres psql -U resilience_user -d resilience -tAc "SELECT count(*) FROM remediation_actions WHERE pipeline_id = '$pipeline_id' AND action = 'increase_timeout_and_retry' AND status = 'success';" | tr -d '[:space:]')
            if [ "$row_count" != "" ] && [ "$row_count" -ge 1 ]; then
              echo "Timeout remediation row present for pipeline_id=$pipeline_id: $row_count"
              exit 0
            fi
            sleep 3
          done
          echo "No timeout remediation row found in Postgres for pipeline_id=$pipeline_id" >&2
          exit 1
        '''
      }
    }
  }

  post {
    always {
      // Always clean containers and volumes to keep agents stateless between builds.
      sh 'docker compose down -v'
    }
  }
}

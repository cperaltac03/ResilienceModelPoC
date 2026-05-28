pipeline {
  agent any

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python') {
      steps {
        sh 'python3 -m pip install --upgrade pip'
      }
    }

    stage('Install dependencies') {
      steps {
        sh 'pip install -r requirements-test.txt'
      }
    }

    stage('Start Docker Compose') {
      steps {
        sh 'docker compose up -d'
      }
    }

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

    stage('Run tests') {
      steps {
        sh 'pytest tests'
      }
    }

    stage('Trigger webhook and validate') {
      steps {
        sh '''
          curl -sS -X POST http://localhost:8001/simulate \
            -H "Content-Type: application/json" \
            -d '{"status":"failed","dependency":"requests","version":"2.31.0"}'

          for i in $(seq 1 20); do
            row_count=$(docker exec postgres psql -U resilience_user -d resilience -tAc "SELECT count(*) FROM remediation_actions;" | tr -d '[:space:]')
            if [ "$row_count" != "" ] && [ "$row_count" -ge 1 ]; then
              echo "Remediation row present: $row_count"
              exit 0
            fi
            sleep 3
          done
          echo "No remediation row found in Postgres" >&2
          exit 1
        '''
      }
    }
  }

  post {
    always {
      sh 'docker compose down -v'
    }
  }
}

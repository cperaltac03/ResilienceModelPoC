#!/usr/bin/env python3
import subprocess
import json
import time
import sys

def run(cmd, shell=False):
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

# Check docker compose status
stdout, stderr, _ = run(['docker', 'compose', 'ps', '--format', 'json'])
if stdout:
    try:
        services = json.loads(stdout)
        print("\n=== DOCKER COMPOSE STATUS ===")
        for svc in services:
            status = svc.get('State', 'unknown')
            name = svc.get('Service', '?')
            print(f"  {name:30} {status}")
    except:
        print(stdout)

# Check simulator health
print("\n=== SIMULATOR HEALTH ===")
for i in range(3):
    stdout, stderr, code = run(['curl', '-s', 'http://localhost:8001/health'])
    if code == 0:
        print(f"  ✓ {stdout}")
        break
    else:
        print(f"  Attempt {i+1}: {stderr}")
        time.sleep(1)

# Check postgres for remediation actions
print("\n=== REMEDIATION ACTIONS IN POSTGRES ===")
sql = "SELECT count(*) FROM remediation_actions;"
cmd = ['docker', 'exec', 'postgres', 'psql', '-U', 'resilience_user', '-d', 'resilience', '-tAc', sql]
stdout, stderr, code = run(cmd)
if code == 0:
    print(f"  Remediation rows: {stdout}")
else:
    print(f"  Error: {stderr}")

# Collect service logs (last 30 lines each)
services = ['pipeline_simulator', 'failure_solver', 'decision_engine', 'failure_classifier']
for svc in services:
    print(f"\n=== LOGS: {svc} (last 30 lines) ===")
    stdout, _, _ = run(['docker', 'compose', 'logs', '--no-color', '--tail=30', svc])
    if stdout:
        print(stdout)
    else:
        print("  (no logs)")

# Defensive Load Test Runbook

## Preconditions

1. Authorized scope approved (`../governance/AUTHORIZED_TEST_SCOPE_TEMPLATE.md`).
2. Environment is staging.
3. Max traffic budget is 20 RPS.
4. On-call and rollback owner are active.

## k6 Execution

```bash
k6 run security/load/k6_api_scenarios.js \
  -e BASE_URL=http://localhost:8000 \
  -e AUTH_TOKEN=<token>
```

## JMeter Execution (Non-GUI)

```bash
jmeter -n \
  -t security/load/jmeter_test_plan_template.jmx \
  -JBASE_URL=http://localhost:8000 \
  -JAUTH_TOKEN=<token> \
  -l security/load/results.jtl
```

## Kill Switch

Stop immediately if rollback triggers fire:

- `Ctrl+C` in active generator terminal
- terminate generator process from CI/runner
- notify incident channel

## Rollback Criteria

- 5xx > 2% for 3 minutes
- p99 latency > 3000 ms for 5 minutes
- timeout rate > 1% for 3 minutes
- critical health checks fail

## Evidence Collection

- Test config snapshot
- Runtime metrics (latency/error/timeouts)
- Infrastructure signals (CPU, memory, DB contention)
- Incident timeline if aborted

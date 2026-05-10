# Load & Resilience Guardrails (Defensive)

## Approved Default Baseline

- Environment: **Staging only**
- Max request rate: **20 RPS**
- Default test window: Business-approved maintenance or low-traffic window

## Traffic Profiles

| Profile | Purpose | Duration | RPS Ceiling | Gate to Continue |
|---|---|---|---|---|
| Smoke | Validate setup and observability | 5 min | 5 | Error rate < 1% |
| Baseline | Establish normal behavior | 15 min | 10 | p95 latency and error budget within target |
| Stress | Find degradation threshold | 20 min | 20 | No critical instability |
| Soak | Detect long-run regressions | 60 min | 8 | Stable resources over time |

## Ramp Policy

1. Start at 1 RPS.
2. Increase by 2 RPS every 2 minutes.
3. Hold at each stage and evaluate SLO/error thresholds.
4. Abort immediately on rollback trigger.

## Core Pass/Fail Thresholds

- HTTP non-2xx/3xx rate: <= 1%
- p95 latency: <= 1000 ms (service-specific override allowed)
- p99 latency: <= 2000 ms
- Timeout rate: <= 0.5%
- Sustained CPU threshold: <= 85% for app nodes
- DB saturation threshold: no sustained lock/contention alerts

## Rollback Triggers

Any one condition should trigger rollback/abort:

- 5xx error rate > 2% for 3 consecutive minutes
- p99 latency > 3000 ms for 5 consecutive minutes
- Elevated timeouts > 1% for 3 consecutive minutes
- Resource exhaustion alerts (CPU > 90%, memory pressure, DB lock spikes)
- Service health-check failures in critical path endpoints

## Rollback Actions

1. Stop all active test generators.
2. Revert to last known stable deployment/config.
3. Verify core endpoint health and error rate normalization.
4. Notify on-call + stakeholders with incident summary.
5. Record timeline and affected metrics for postmortem.

## Production Testing Rule

Production testing is prohibited by default and requires:

- explicit written approval
- reduced RPS cap (separate sign-off)
- incident commander assigned
- rollback authority available in real time


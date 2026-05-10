# Security & Resilience Assessment Report Template

## 1. Executive Summary

- Assessment name:
- Date range:
- Environment:
- Scope summary:
- Overall risk rating:
- Go/No-Go recommendation:

## 2. Methodology

- Load/resilience approach (k6/JMeter profiles used):
- Non-intrusive security checks performed:
- Standards mapping (OWASP ASVS/SAMM):
- Tooling used:
- Limitations/assumptions:

## 3. Risk Rating Model

Use a 5-point scale per finding:

- **Impact (1-5)**
- **Likelihood (1-5)**
- **Risk Score = Impact x Likelihood**

Severity mapping:

- 16-25: Critical
- 10-15: High
- 6-9: Medium
- 1-5: Low

## 4. Findings Table

| ID | Category | Asset | Evidence | Impact | Likelihood | Risk Score | Severity | Recommendation | Owner | Due Date | Status |
|---|---|---|---|---:|---:|---:|---|---|---|---|---|
| F-001 |  |  |  |  |  |  |  |  |  |  |  |

## 5. Resilience Outcomes

| Profile | Target RPS | Achieved RPS | Error Rate | p95 Latency | p99 Latency | Outcome |
|---|---:|---:|---:|---:|---:|---|
| Smoke | 5 |  |  |  |  |  |
| Baseline | 10 |  |  |  |  |  |
| Stress | 20 |  |  |  |  |  |
| Soak | 8 |  |  |  |  |  |

## 6. Remediation Plan

| Finding ID | Action | Priority | Owner | Target Date | Dependencies |
|---|---|---|---|---|---|
| F-001 |  |  |  |  |  |

## 7. Re-Test Verification

| Finding ID | Re-Test Date | Test Evidence | Result (Pass/Fail) | Verifier | Closure Notes |
|---|---|---|---|---|---|
| F-001 |  |  |  |  |  |

## 8. Closure Criteria

- Critical: fixed + verified before release.
- High: fixed + verified in agreed sprint window.
- Medium: mitigated or accepted with documented rationale.
- Low: tracked in backlog with ownership.

## 9. Approvals

- Security lead:
- Engineering manager:
- Product owner:


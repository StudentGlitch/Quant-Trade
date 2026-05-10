# Authorized Security & Resilience Testing Scope Template

## 1. Authorization

- Requesting organization:
- Asset owner:
- Legal approver (name/title/signature):
- Technical approver (name/title/signature):
- Authorization reference ID:
- Approval date:
- Validity window:

## 2. Engagement Metadata

- Engagement name:
- Primary objective:
- Engagement type: Defensive assessment (non-intrusive)
- Environment: Staging only (default) / Approved production window
- Start date/time (timezone):
- End date/time (timezone):

## 3. In-Scope Assets

| Asset Type | Identifier | Notes |
|---|---|---|
| Domain/Subdomain |  |  |
| API Base URL |  |  |
| Service Host/IP |  |  |
| Port/Protocol |  |  |
| Mobile/Web App |  |  |

## 4. Explicit Out-of-Scope

- Data exfiltration attempts
- Privilege escalation attempts
- Destructive payloads
- Credential stuffing/brute-force
- Social engineering
- Third-party services not explicitly listed as in-scope

## 5. Allowed Activities

- Load/resilience testing within approved traffic budgets
- Header/TLS/configuration checks
- Dependency and SBOM vulnerability scanning
- OWASP ASVS/SAMM control review

## 6. Prohibited Activities

- Exploit development
- Zero-day weaponization
- Persistence mechanisms
- Any action that modifies production data

## 7. Source IP Allowlist

| Scanner Hostname | Public IP | Purpose | Approved |
|---|---|---|---|
|  |  |  |  |

## 8. Traffic Safety Controls

- Max RPS (default): 20 (staging)
- Concurrency cap:
- Ramp-up schedule:
- Error budget threshold:
- Stop condition:
- Rollback authority:

## 9. Incident & Escalation

- Incident channel:
- On-call contacts:
- Escalation sequence:
- Decision SLA:

## 10. Data Handling Rules

- No sensitive data extraction.
- Redact PII/secrets in logs and screenshots.
- Store evidence in approved encrypted location only.
- Retention period:
- Disposal method:

## 11. Coordinated Disclosure Workflow

1. Submit finding to asset owner.
2. Confirm severity and impact.
3. Assign remediation owner and target date.
4. Re-test after fix.
5. Close with evidence.

## 12. Sign-Off

- Legal approval:
- Security lead approval:
- Engineering owner approval:


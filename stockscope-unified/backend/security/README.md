# Backend Security Assurance Pack

This folder contains defensive artifacts for authorized resilience and security assessment.

## Structure

- `governance/`
  - `AUTHORIZED_TEST_SCOPE_TEMPLATE.md`
  - `PENTEST_AUTHORIZATION_TEMPLATE.md`
- `load/`
  - `LOAD_GUARDRAILS.md`
  - `k6_api_scenarios.js`
  - `jmeter_test_plan_template.jmx`
  - `RUNBOOK.md`
- `checks/`
  - `ASVS_SAMM_BASELINE_CHECKLIST.md`
  - `baseline_report.sample.json` (generated sample output)
- `scripts/`
  - `non_intrusive_security_baseline.py`
- `reporting/`
  - `SECURITY_ASSESSMENT_REPORT_TEMPLATE.md`
  - `findings_template.csv`

## Quick Start

1. Fill authorization templates in `governance/`.
2. Confirm guardrails in `load/LOAD_GUARDRAILS.md`.
3. Run non-intrusive baseline:

```bash
python security/scripts/non_intrusive_security_baseline.py \
  --base-url https://staging.example.com \
  --requirements-path requirements.txt \
  --output security/checks/baseline_report.json
```

4. Execute load profiles with k6/JMeter using `load/RUNBOOK.md`.
5. Capture findings using `reporting/SECURITY_ASSESSMENT_REPORT_TEMPLATE.md`.


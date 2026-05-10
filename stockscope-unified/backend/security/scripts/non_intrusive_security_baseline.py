import argparse
import json
import socket
import ssl
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


REQUIRED_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
]


@dataclass
class CheckResult:
    name: str
    status: str
    details: Dict[str, object]


def fetch_headers(url: str, timeout: int) -> CheckResult:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers.items())
            missing = [h for h in REQUIRED_HEADERS if h not in headers]
            return CheckResult(
                name="http_headers",
                status="pass" if not missing else "partial",
                details={
                    "status_code": resp.status,
                    "missing_headers": missing,
                    "headers": headers,
                },
            )
    except HTTPError as e:
        return CheckResult(
            name="http_headers",
            status="fail",
            details={"error": f"HTTPError {e.code}", "reason": str(e)},
        )
    except URLError as e:
        return CheckResult(
            name="http_headers",
            status="fail",
            details={"error": "URLError", "reason": str(e)},
        )


def tls_check(url: str, timeout: int) -> CheckResult:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host or parsed.scheme != "https":
        return CheckResult(
            name="tls_certificate",
            status="partial",
            details={"reason": "TLS check skipped because URL is not HTTPS"},
        )

    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as secure_sock:
                cert = secure_sock.getpeercert()
                tls_version = secure_sock.version()
                cipher = secure_sock.cipher()
                return CheckResult(
                    name="tls_certificate",
                    status="pass",
                    details={
                        "tls_version": tls_version,
                        "cipher": cipher[0] if cipher else None,
                        "issuer": cert.get("issuer"),
                        "subject": cert.get("subject"),
                        "not_after": cert.get("notAfter"),
                    },
                )
    except Exception as exc:
        return CheckResult(
            name="tls_certificate",
            status="fail",
            details={"error": str(exc)},
        )


def dependency_scan(requirements_path: Path) -> CheckResult:
    if not requirements_path.exists():
        return CheckResult(
            name="dependency_scan",
            status="fail",
            details={"error": f"Requirements file not found: {requirements_path}"},
        )

    result: Dict[str, object] = {
        "requirements_path": str(requirements_path),
        "pip_audit_available": False,
        "pip_audit_output": None,
    }
    try:
        cmd = [sys.executable, "-m", "pip_audit", "-r", str(requirements_path), "--format", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        result["pip_audit_available"] = proc.returncode in (0, 1)
        result["pip_audit_stdout"] = proc.stdout
        result["pip_audit_stderr"] = proc.stderr
        status = "pass" if proc.returncode == 0 else "partial"
        return CheckResult(name="dependency_scan", status=status, details=result)
    except Exception as exc:
        result["pip_audit_error"] = str(exc)
        result["hint"] = "Install pip-audit for CVE checks: pip install pip-audit"
        return CheckResult(name="dependency_scan", status="partial", details=result)


def sbom_snapshot() -> CheckResult:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return CheckResult(
                name="sbom_snapshot",
                status="fail",
                details={"error": proc.stderr},
            )
        packages = json.loads(proc.stdout)
        return CheckResult(
            name="sbom_snapshot",
            status="pass",
            details={"package_count": len(packages), "packages": packages},
        )
    except Exception as exc:
        return CheckResult(
            name="sbom_snapshot",
            status="fail",
            details={"error": str(exc)},
        )


def run_checks(base_url: str, requirements_path: Path, timeout: int) -> List[CheckResult]:
    return [
        fetch_headers(base_url, timeout=timeout),
        tls_check(base_url, timeout=timeout),
        dependency_scan(requirements_path=requirements_path),
        sbom_snapshot(),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run non-intrusive security baseline checks.")
    parser.add_argument("--base-url", required=True, help="Target base URL (staging recommended).")
    parser.add_argument(
        "--requirements-path",
        default=str(Path(__file__).resolve().parents[2] / "requirements.txt"),
        help="Path to requirements.txt for dependency scan.",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "checks" / "baseline_report.json"),
        help="Output report path.",
    )
    parser.add_argument("--timeout", type=int, default=10, help="Network timeout in seconds.")
    args = parser.parse_args()

    checks = run_checks(
        base_url=args.base_url,
        requirements_path=Path(args.requirements_path),
        timeout=args.timeout,
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": args.base_url,
        "mode": "non-intrusive",
        "results": [asdict(check) for check in checks],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Baseline report written to: {output_path}")


if __name__ == "__main__":
    main()

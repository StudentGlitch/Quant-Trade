import argparse
import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "swarm_state.db"
LOG_PATH = BASE_DIR / "logs" / "system_execution.log"
REVENUE_PATH = BASE_DIR / "logs" / "revenue_tracker.csv"


def _safe_int(value: str | None, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(min(parsed, max_value), min_value)


def _tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-limit:]]


def _read_status_counts() -> dict:
    counts = Counter(
        {
            "DISCOVERED": 0,
            "SOLVING": 0,
            "READY_FOR_VERIFICATION": 0,
            "VERIFYING": 0,
            "READY_FOR_SUBMISSION": 0,
            "SUBMITTED_UNVERIFIED": 0,
            "SUBMITTED": 0,
            "FAILED": 0,
            "BLOCKED": 0,
        }
    )
    if not DB_PATH.exists():
        return dict(counts)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT status, COUNT(*) FROM bounties GROUP BY status")
        for status, total in cur.fetchall():
            counts[status] = total
    return dict(counts)


def _read_recent_bounties(limit: int) -> list[dict]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, platform, url, description, reward_estimate, status, discovered_at, submitted_at
            FROM bounties
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def _read_recent_submitted(limit: int) -> list[dict]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, platform, url, reward_estimate, submitted_at
            FROM bounties
            WHERE status = 'SUBMITTED'
            ORDER BY submitted_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def _read_recent_revenue(limit: int) -> list[dict]:
    if not REVENUE_PATH.exists():
        return []
    with REVENUE_PATH.open("r", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _read_truth_metrics() -> dict:
    if not DB_PATH.exists():
        return {
            "solved_threshold": "L3",
            "total_bounties": 0,
            "submitted_attempts": 0,
            "submitted_unverified": 0,
            "solved_l3_count": 0,
            "acceptance_rate": 0.0,
            "verification_pass_rate": 0.0,
            "verifier_error_count": 0,
        }

    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM bounties").fetchone()[0]
        submitted = conn.execute("SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED'").fetchone()[0]
        submitted_unverified = conn.execute(
            "SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED_UNVERIFIED'"
        ).fetchone()[0]
        solved_l3 = conn.execute(
            "SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED' AND proof_link IS NOT NULL"
        ).fetchone()[0]

        verification_pass_rate = 0.0
        if _table_exists(conn, "verification_logs"):
            passed, all_logs = conn.execute(
                "SELECT SUM(passed), COUNT(*) FROM verification_logs"
            ).fetchone()
            if all_logs:
                verification_pass_rate = float(passed or 0) / float(all_logs)

    submitted_attempts = submitted + submitted_unverified
    acceptance_rate = (solved_l3 / submitted_attempts) if submitted_attempts else 0.0
    verifier_errors = sum(1 for line in _tail_lines(LOG_PATH, 400) if "Error saving verification" in line)

    return {
        "solved_threshold": "L3",
        "total_bounties": total,
        "submitted_attempts": submitted_attempts,
        "submitted_unverified": submitted_unverified,
        "solved_l3_count": solved_l3,
        "acceptance_rate": round(acceptance_rate, 3),
        "verification_pass_rate": round(verification_pass_rate, 3),
        "verifier_error_count": verifier_errors,
    }


def _read_verifier_health() -> dict:
    defaults = {
        "runs_last_60m": 0,
        "empty_runs_last_60m": 0,
        "processed_last_60m": 0,
        "last_run_at": None,
        "last_run_queue_size": 0,
        "last_run_processed": 0,
        "last_run_failed": 0,
        "last_run_elapsed_ms": 0,
        "ready_for_verification": 0,
        "oldest_ready_for_verification_min": None,
    }
    if not DB_PATH.exists():
        return defaults

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ready = conn.execute(
            "SELECT COUNT(*) FROM bounties WHERE status='READY_FOR_VERIFICATION'"
        ).fetchone()[0]
        oldest = conn.execute(
            """
            SELECT CAST((julianday('now') - julianday(discovered_at)) * 24 * 60 AS INTEGER)
            FROM bounties
            WHERE status='READY_FOR_VERIFICATION'
            ORDER BY discovered_at ASC
            LIMIT 1
            """
        ).fetchone()

        if not _table_exists(conn, "verifier_runs"):
            defaults["ready_for_verification"] = ready
            defaults["oldest_ready_for_verification_min"] = oldest[0] if oldest else None
            return defaults

        runs = conn.execute(
            """
            SELECT
                COUNT(*) AS runs,
                COALESCE(SUM(empty_run), 0) AS empty_runs,
                COALESCE(SUM(processed_count), 0) AS processed
            FROM verifier_runs
            WHERE created_at >= datetime('now', '-60 minutes')
            """
        ).fetchone()
        latest = conn.execute(
            """
            SELECT created_at, queue_size, processed_count, failed_count, elapsed_ms
            FROM verifier_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    return {
        "runs_last_60m": runs["runs"] if runs else 0,
        "empty_runs_last_60m": runs["empty_runs"] if runs else 0,
        "processed_last_60m": runs["processed"] if runs else 0,
        "last_run_at": latest["created_at"] if latest else None,
        "last_run_queue_size": latest["queue_size"] if latest else 0,
        "last_run_processed": latest["processed_count"] if latest else 0,
        "last_run_failed": latest["failed_count"] if latest else 0,
        "last_run_elapsed_ms": latest["elapsed_ms"] if latest else 0,
        "ready_for_verification": ready,
        "oldest_ready_for_verification_min": oldest[0] if oldest else None,
    }


def _read_recent_verifications(limit: int) -> list[dict]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if not _table_exists(conn, "verification_logs"):
            return []
        cur = conn.execute(
            """
            SELECT v.bounty_id, v.score, v.confidence_level, v.hard_fail, v.passed, v.reasons, v.created_at
            FROM verification_logs v
            ORDER BY v.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def build_snapshot(
    log_lines: int = 40,
    bounty_limit: int = 20,
    submitted_limit: int = 10,
    revenue_limit: int = 10,
    verification_limit: int = 10,
) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_counts": _read_status_counts(),
        "truth_metrics": _read_truth_metrics(),
        "verifier_health": _read_verifier_health(),
        "recent_bounties": _read_recent_bounties(bounty_limit),
        "recent_submitted": _read_recent_submitted(submitted_limit),
        "recent_revenue": _read_recent_revenue(revenue_limit),
        "recent_verifications": _read_recent_verifications(verification_limit),
        "recent_logs": _tail_lines(LOG_PATH, log_lines),
    }


def _json_response(handler: BaseHTTPRequestHandler, payload: dict | list, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_response(handler: BaseHTTPRequestHandler, html: str) -> None:
    body = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _dashboard_html(refresh_seconds: int) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Micro-Bounty Swarm Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; background: #111; color: #eee; }}
    .grid {{ display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 8px; }}
    .card {{ background: #1c1c1c; border: 1px solid #333; padding: 10px; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #333; padding: 6px; text-align: left; }}
    th {{ background: #222; }}
    pre {{ background: #0d0d0d; border: 1px solid #333; padding: 10px; overflow: auto; height: 260px; }}
    a {{ color: #88c0ff; }}
    .muted {{ color: #aaa; }}
  </style>
</head>
<body>
  <h2>Micro-Bounty Swarm Dashboard</h2>
  <div class="muted">Auto-refresh every {refresh_seconds}s • Localhost read-only monitor</div>
  <h3>Status</h3>
  <div id="status" class="grid"></div>
  <h3>Truth Metrics (L3)</h3>
  <div id="truth" class="grid"></div>
  <h3>Verifier Health</h3>
  <div id="verifier" class="grid"></div>
  <h3>Recent Bounties</h3>
  <table id="bounties"></table>
  <h3>Recent Submissions</h3>
  <table id="submitted"></table>
  <h3>Recent Verifications</h3>
  <table id="verifications"></table>
  <h3>Revenue Tracker (tail)</h3>
  <table id="revenue"></table>
  <h3>System Logs (tail)</h3>
  <pre id="logs"></pre>
<script>
const refreshMs = {refresh_seconds} * 1000;
function esc(s) {{
  if (s === null || s === undefined) return "";
  return String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}}
function renderTable(el, rows, cols) {{
  const head = "<tr>" + cols.map(c => `<th>${{esc(c)}}</th>`).join("") + "</tr>";
  const body = rows.map(r => "<tr>" + cols.map(c => `<td>${{esc(r[c])}}</td>`).join("") + "</tr>").join("");
  el.innerHTML = head + body;
}}
async function refresh() {{
  const r = await fetch("/api/snapshot?logs=50&bounties=20&submitted=10&revenue=10&verifications=10");
  const data = await r.json();
  const status = data.status_counts || {{}};
  document.getElementById("status").innerHTML = Object.keys(status).map(k =>
    `<div class="card"><div>${{esc(k)}}</div><div style="font-size:22px;font-weight:bold">${{esc(status[k])}}</div></div>`
  ).join("");
  const truth = data.truth_metrics || {{}};
  document.getElementById("truth").innerHTML = Object.keys(truth).map(k =>
    `<div class="card"><div>${{esc(k)}}</div><div style="font-size:18px;font-weight:bold">${{esc(truth[k])}}</div></div>`
  ).join("");
  const verifier = data.verifier_health || {{}};
  document.getElementById("verifier").innerHTML = Object.keys(verifier).map(k =>
    `<div class="card"><div>${{esc(k)}}</div><div style="font-size:18px;font-weight:bold">${{esc(verifier[k])}}</div></div>`
  ).join("");
  renderTable(document.getElementById("bounties"), data.recent_bounties || [], ["id","platform","status","reward_estimate","discovered_at","submitted_at","url"]);
  renderTable(document.getElementById("submitted"), data.recent_submitted || [], ["id","platform","reward_estimate","submitted_at","url"]);
  renderTable(document.getElementById("verifications"), data.recent_verifications || [], ["bounty_id","score","confidence_level","hard_fail","passed","reasons","created_at"]);
  renderTable(document.getElementById("revenue"), data.recent_revenue || [], ["timestamp","bounty_id","platform","estimated_reward","url"]);
  document.getElementById("logs").textContent = (data.recent_logs || []).join("\\n");
}}
refresh();
setInterval(refresh, refreshMs);
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    refresh_seconds = 5

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route == "/":
            _html_response(self, _dashboard_html(self.refresh_seconds))
            return

        if route == "/api/snapshot":
            payload = build_snapshot(
                log_lines=_safe_int((query.get("logs") or [None])[0], 40, 10, 500),
                bounty_limit=_safe_int((query.get("bounties") or [None])[0], 20, 5, 200),
                submitted_limit=_safe_int((query.get("submitted") or [None])[0], 10, 5, 100),
                revenue_limit=_safe_int((query.get("revenue") or [None])[0], 10, 5, 100),
                verification_limit=_safe_int((query.get("verifications") or [None])[0], 10, 5, 100),
            )
            _json_response(self, payload)
            return

        if route == "/healthz":
            _json_response(self, {"ok": True})
            return

        _json_response(self, {"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:
        return


def run_dashboard(host: str = "127.0.0.1", port: int = 8787, refresh_seconds: int = 5) -> None:
    DashboardHandler.refresh_seconds = refresh_seconds
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local monitoring dashboard for micro-bounty-swarm.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--refresh-seconds", type=int, default=5)
    args = parser.parse_args()
    run_dashboard(host=args.host, port=args.port, refresh_seconds=args.refresh_seconds)


if __name__ == "__main__":
    main()

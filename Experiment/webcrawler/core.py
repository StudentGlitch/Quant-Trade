"""Core transport, metadata, and download logic for the IDX crawler."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import NameResolutionError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from requests import Request

from .utils import (
    CSV_FIELDS,
    append_csv_row,
    checksum_file,
    ensure_dir,
    ensure_parent_dir,
    read_csv_rows,
    sanitize_filename,
    utc_timestamp,
)


IDX_BASE_URL = "https://www.idx.co.id"
IDX_REPORT_PAGE_URL = (
    f"{IDX_BASE_URL}/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan/"
)
IDX_FINANCIAL_REPORT_ENDPOINT = (
    f"{IDX_BASE_URL}/primary/ListedCompany/GetFinancialReport"
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
DEFAULT_REPORT_TYPES = ("annualreport", "annual-report", "annual", "ar")
STATUS_SUCCESS = "Success"
STATUS_SKIPPED = "Skipped"
STATUS_BLOCKED = "Blocked"
STATUS_BLOCKED_CLOUDFLARE = "Blocked_Cloudflare"
STATUS_FAILED = "Failed"
STATUS_FAILED_DNS = "Failed_DNS"
STATUS_FILE_NOT_FOUND = "File_Not_Found"


class IDXError(RuntimeError):
    """Base IDX crawler error."""


class IDXBlockedError(IDXError):
    """Raised when IDX blocks the crawler."""


class IDXFileNotFoundError(IDXError):
    """Raised when the report file or metadata URL does not exist."""


@dataclass(frozen=True)
class AnnualReport:
    ticker: str
    year: int
    company: str
    title: str
    report_url: str

    @property
    def file_name(self) -> str:
        return sanitize_filename(f"{self.ticker}_{self.year}.pdf")


@dataclass
class DownloadResult:
    ticker: str
    year: int
    file_path: str
    status: str
    checksum: str
    timestamp: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "ticker": self.ticker,
            "year": str(self.year),
            "file_path": self.file_path,
            "status": self.status,
            "checksum": self.checksum,
            "timestamp": self.timestamp,
        }


class MetadataStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.rows = read_csv_rows(self.path)
        self.latest: dict[tuple[str, int], dict[str, str]] = {}
        for row in self.rows:
            ticker = row.get("ticker", "").strip().upper()
            year_text = row.get("year", "").strip()
            if not ticker or not year_text.isdigit():
                continue
            self.latest[(ticker, int(year_text))] = row

    def get(self, ticker: str, year: int) -> dict[str, str] | None:
        return self.latest.get((ticker.upper(), int(year)))

    def has_valid_download(self, ticker: str, year: int) -> bool:
        row = self.get(ticker, year)
        if not row:
            return False
        if row.get("status") not in {STATUS_SUCCESS, STATUS_SKIPPED}:
            return False
        file_path = row.get("file_path", "")
        checksum = row.get("checksum", "")
        if not file_path or not checksum:
            return False
        file_on_disk = Path(file_path)
        if not file_on_disk.exists():
            return False
        try:
            return checksum_file(file_on_disk) == checksum
        except OSError:
            return False

    def append(self, result: DownloadResult) -> None:
        row = result.to_csv_row()
        append_csv_row(self.path, row)
        self.latest[(result.ticker.upper(), int(result.year))] = row


def build_session(
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    cookie_header: str = "",
) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": IDX_REPORT_PAGE_URL,
            "User-Agent": user_agent,
        }
    )
    if cookie_header:
        session.headers["Cookie"] = cookie_header
        for cookie in parse_cookie_header(cookie_header):
            session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])
    return session


def parse_cookie_header(cookie_header: str, domain: str = ".idx.co.id") -> list[dict[str, str]]:
    cookies: list[dict[str, str]] = []
    for item in cookie_header.split(";"):
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        key = name.strip()
        val = value.strip()
        if key:
            cookies.append({"name": key, "value": val, "domain": domain})
    return cookies


def absolute_idx_url(path_or_url: str) -> str:
    return urljoin(IDX_BASE_URL, path_or_url.strip())


def extract_result_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("Results", "results", "Result", "result", "data", "Data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_result_rows(value)
            if nested:
                return nested
    return []


def is_cloudflare_blocked(response: requests.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        return False
    text = response.text[:500].lower()
    return "cloudflare" in text or "attention required" in text


def is_blocked_response(response: requests.Response) -> bool:
    return response.status_code in {403, 503} or is_cloudflare_blocked(response)


def normalize_reports(
    rows: Iterable[dict[str, Any]],
    *,
    fallback_ticker: str,
    fallback_year: int,
) -> list[AnnualReport]:
    reports: list[AnnualReport] = []
    for row in rows:
        ticker = _first_text(row, "KodeEmiten", "kodeEmiten") or fallback_ticker
        year_text = _first_text(row, "TahunBuku", "tahunBuku", "year")
        year = int(year_text) if year_text else fallback_year
        company = _first_text(row, "NamaEmiten", "namaEmiten", "CompanyName")
        title = _first_text(row, "Judul", "Title", "NamaDokumen", "DocumentName")
        for attachment in _iter_attachments(row):
            report_url = _attachment_url(attachment)
            if not report_url:
                continue
            reports.append(
                AnnualReport(
                    ticker=ticker,
                    year=year,
                    company=company,
                    title=title or sanitize_filename(report_url.split("/")[-1]),
                    report_url=report_url,
                )
            )
    return reports


def fetch_annual_report(
    ticker: str,
    year: int,
    *,
    session: requests.Session,
    report_types: Iterable[str] = DEFAULT_REPORT_TYPES,
    timeout: int = 30,
    use_browser_fallback: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
) -> AnnualReport | None:
    for report_type in report_types:
        params = {
            "indexFrom": 0,
            "pageSize": 100,
            "year": int(year),
            "reportType": report_type,
            "kodeEmiten": ticker,
        }
        rows = _fetch_report_rows(
            session,
            params=params,
            timeout=timeout,
            use_browser_fallback=use_browser_fallback,
            user_agent=user_agent,
        )
        reports = normalize_reports(rows, fallback_ticker=ticker, fallback_year=year)
        if reports:
            return reports[0]
    return None


def run_crawl(
    tickers: Iterable[str],
    years: Iterable[int],
    *,
    metadata_path: str | Path,
    reports_dir: str | Path,
    cookie_header: str = "",
    timeout: int = 30,
    user_agent: str = DEFAULT_USER_AGENT,
    use_browser_fallback: bool = True,
) -> list[DownloadResult]:
    ensure_parent_dir(metadata_path)
    ensure_dir(reports_dir)
    session = build_session(user_agent=user_agent, cookie_header=cookie_header)
    store = MetadataStore(metadata_path)
    results: list[DownloadResult] = []

    ticker_list = list(tickers)
    year_list = list(years)
    total = len(ticker_list) * len(year_list)
    count = 0

    try:
        for ticker in ticker_list:
            for year in year_list:
                count += 1
                print(f"[{count}/{total}] Processing {ticker} {year}...", file=sys.stderr, end="\r")
                result = process_one(
                    ticker,
                    year,
                    store=store,
                    reports_dir=reports_dir,
                    session=session,
                    timeout=timeout,
                    user_agent=user_agent,
                    use_browser_fallback=use_browser_fallback and not bool(cookie_header),
                )
                results.append(result)
        print("", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nidx-annual-reports: crawl interrupted", file=sys.stderr)
        raise

    return results


def process_one(
    ticker: str,
    year: int,
    *,
    store: MetadataStore,
    reports_dir: str | Path,
    session: requests.Session,
    timeout: int,
    user_agent: str,
    use_browser_fallback: bool,
) -> DownloadResult:
    timestamp = utc_timestamp()
    if store.has_valid_download(ticker, year):
        row = store.get(ticker, year) or {}
        result = DownloadResult(
            ticker=ticker,
            year=year,
            file_path=row.get("file_path", ""),
            status="Skipped",
            checksum=row.get("checksum", ""),
            timestamp=timestamp,
        )
        store.append(result)
        return result

    try:
        report = fetch_annual_report(
            ticker,
            year,
            session=session,
            timeout=timeout,
            use_browser_fallback=use_browser_fallback,
            user_agent=user_agent,
        )
        if report is None:
            result = DownloadResult(
                ticker=ticker,
                year=year,
                file_path="",
                status=STATUS_FAILED,
                checksum="",
                timestamp=timestamp,
            )
            store.append(result)
            return result

        target = Path(reports_dir) / report.file_name
        content = _download_report_bytes(
            report.report_url,
            session=session,
            timeout=max(timeout, 60),
            use_browser_fallback=use_browser_fallback,
            user_agent=user_agent,
        )
        ensure_parent_dir(target)
        
        temp_target = target.with_suffix(".tmp")
        try:
            with temp_target.open("wb") as handle:
                handle.write(content)
            temp_target.replace(target)
        finally:
            if temp_target.exists():
                temp_target.unlink()

        checksum = checksum_file(target)
        result = DownloadResult(
            ticker=ticker,
            year=year,
            file_path=str(target),
            status=STATUS_SUCCESS,
            checksum=checksum,
            timestamp=timestamp,
        )
    except IDXBlockedError as exc:
        status = STATUS_BLOCKED_CLOUDFLARE if "cloudflare" in str(exc).lower() else STATUS_BLOCKED
        result = DownloadResult(
            ticker=ticker,
            year=year,
            file_path="",
            status=status,
            checksum="",
            timestamp=timestamp,
        )
    except IDXFileNotFoundError:
        result = DownloadResult(
            ticker=ticker,
            year=year,
            file_path="",
            status=STATUS_FILE_NOT_FOUND,
            checksum="",
            timestamp=timestamp,
        )
    except (requests.RequestException, OSError, IDXError) as exc:
        status = classify_exception_status(exc)
        result = DownloadResult(
            ticker=ticker,
            year=year,
            file_path="",
            status=status,
            checksum="",
            timestamp=timestamp,
        )

    store.append(result)
    return result


def _fetch_report_rows(
    session: requests.Session,
    *,
    params: dict[str, Any],
    timeout: int,
    use_browser_fallback: bool,
    user_agent: str,
) -> list[dict[str, Any]]:
    try:
        response = session.get(IDX_FINANCIAL_REPORT_ENDPOINT, params=params, timeout=timeout)
        if is_cloudflare_blocked(response):
            raise IDXBlockedError("Cloudflare blocked the metadata request.")
        if is_blocked_response(response):
            raise IDXBlockedError("IDX blocked the metadata request.")
        if response.status_code == 404:
            raise IDXFileNotFoundError("IDX metadata endpoint returned 404.")
        response.raise_for_status()
        return extract_result_rows(response.json())
    except (requests.RequestException, ValueError, IDXBlockedError):
        if not use_browser_fallback:
            raise
        return _fetch_report_rows_via_playwright(params=params, user_agent=user_agent)


def _download_report_bytes(
    report_url: str,
    *,
    session: requests.Session,
    timeout: int,
    use_browser_fallback: bool,
    user_agent: str,
) -> bytes:
    try:
        response = session.get(report_url, timeout=timeout, stream=True)
        if is_cloudflare_blocked(response):
            raise IDXBlockedError("Cloudflare blocked the PDF download.")
        if is_blocked_response(response):
            raise IDXBlockedError("IDX blocked the PDF download.")
        if response.status_code == 404:
            raise IDXFileNotFoundError("IDX PDF returned 404.")
        response.raise_for_status()
        return response.content
    except (requests.RequestException, IDXBlockedError):
        if not use_browser_fallback:
            raise
        return _playwright_get_bytes(
            report_url,
            user_agent=user_agent,
            timeout_ms=max(timeout * 1000, 60_000),
        )


def _fetch_report_rows_via_playwright(
    *,
    params: dict[str, Any],
    user_agent: str,
) -> list[dict[str, Any]]:
    url = Request("GET", IDX_FINANCIAL_REPORT_ENDPOINT, params=params).prepare().url
    if not url:
        return []
    payload = _playwright_get_json(url, user_agent=user_agent)
    return extract_result_rows(payload)


def _playwright_get_json(
    url: str,
    *,
    user_agent: str,
    timeout_ms: int = 90_000,
) -> Any:
    body = _playwright_get_bytes(url, user_agent=user_agent, timeout_ms=timeout_ms)
    try:
        return requests.models.complexjson.loads(body.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise IDXError(f"Playwright returned non-JSON response for {url}") from exc


def _playwright_get_bytes(
    url: str,
    *,
    user_agent: str,
    timeout_ms: int = 90_000,
) -> bytes:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()
                page.goto(IDX_REPORT_PAGE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
                response = context.request.get(url, timeout=timeout_ms)
                if response.status in {403, 503}:
                    raise IDXBlockedError("IDX blocked the browser-context request.")
                if response.status == 404:
                    raise IDXFileNotFoundError("IDX browser-context request returned 404.")
                if not response.ok:
                    raise requests.HTTPError(f"http {response.status}")
                return response.body()
            except PlaywrightTimeoutError as exc:
                raise IDXBlockedError(f"Playwright request timed out: {exc}") from exc
            finally:
                browser.close()
    except IDXError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise IDXError(f"Playwright request failed: {exc}") from exc


def classify_exception_status(exc: BaseException) -> str:
    if isinstance(exc, IDXBlockedError):
        return STATUS_BLOCKED_CLOUDFLARE
    if isinstance(exc, IDXFileNotFoundError):
        return STATUS_FILE_NOT_FOUND
    if _is_dns_error(exc):
        return STATUS_FAILED_DNS
    return STATUS_FAILED


def _is_dns_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, NameResolutionError):
            return True
        if isinstance(current, RequestsConnectionError) and "NameResolutionError" in str(current):
            return True
        if isinstance(current, OSError) and getattr(current, "errno", None) in {11001, -2}:
            return True
        for arg in getattr(current, "args", ()):
            if isinstance(arg, NameResolutionError):
                return True
            if isinstance(arg, OSError) and getattr(arg, "errno", None) in {11001, -2}:
                return True
        current = current.__cause__ or current.__context__
    return False


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _iter_attachments(row: dict[str, Any]) -> list[Any]:
    for key in ("Attachments", "attachments", "Files", "files"):
        value = row.get(key)
        if isinstance(value, list):
            return value
    return []


def _attachment_url(attachment: Any) -> str:
    if isinstance(attachment, str):
        return absolute_idx_url(attachment)
    if not isinstance(attachment, dict):
        return ""
    for key in ("File_Path", "FullSavePath", "Url", "url", "Link", "link"):
        value = attachment.get(key)
        if value:
            return absolute_idx_url(str(value))
    return ""

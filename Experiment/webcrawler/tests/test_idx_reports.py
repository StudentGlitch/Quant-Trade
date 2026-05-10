import io
import socket

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import NameResolutionError

from webcrawler.cli import main
from webcrawler.core import (
    AnnualReport,
    IDXBlockedError,
    IDXFileNotFoundError,
    MetadataStore,
    absolute_idx_url,
    classify_exception_status,
    extract_result_rows,
    is_blocked_response,
    normalize_reports,
)
from webcrawler.idx_reports import _absolute_idx_url, _extract_result_rows, _parse_years, _reports_from_rows
from webcrawler.utils import checksum_file, load_tickers_from_sources, parse_years


class FakeResponse:
    def __init__(
        self,
        *,
        status_code=200,
        headers=None,
        text="",
        json_data=None,
        content=b"",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self._json_data = json_data
        self.content = content

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}")


def test_parse_years_accepts_ranges_and_lists():
    assert parse_years("2021,2023-2024") == [2021, 2023, 2024]
    assert _parse_years("2021,2023-2024") == [2021, 2023, 2024]


def test_absolute_idx_url_normalizes_relative_paths():
    expected = "https://www.idx.co.id/StaticData/NewsAndAnnouncement/annual.pdf"
    assert absolute_idx_url("/StaticData/NewsAndAnnouncement/annual.pdf") == expected
    assert _absolute_idx_url("/StaticData/NewsAndAnnouncement/annual.pdf") == expected


def test_extract_result_rows_supports_idx_result_shape():
    payload = {"Results": [{"KodeEmiten": "BBCA"}], "ResultCount": 1}
    assert extract_result_rows(payload) == [{"KodeEmiten": "BBCA"}]
    assert _extract_result_rows(payload) == [{"KodeEmiten": "BBCA"}]


def test_reports_from_rows_normalizes_attachment_metadata():
    rows = [
        {
            "KodeEmiten": "BBCA",
            "NamaEmiten": "Bank Central Asia Tbk",
            "TahunBuku": 2023,
            "Attachments": [
                {"File_Path": "/StaticData/ListedCompanies/AnnualReport/BBCA_2023.pdf"}
            ],
        }
    ]
    reports = normalize_reports(rows, fallback_ticker="BBCA", fallback_year=2023)
    compat = _reports_from_rows(rows, fallback_ticker="BBCA", fallback_year=2023)
    assert reports == compat
    assert reports[0] == AnnualReport(
        ticker="BBCA",
        year=2023,
        company="Bank Central Asia Tbk",
        title="BBCA_2023.pdf",
        report_url="https://www.idx.co.id/StaticData/ListedCompanies/AnnualReport/BBCA_2023.pdf",
    )


def test_load_tickers_filters_invalid_values():
    assert load_tickers_from_sources(["bbca", "bad1", "TLKM", "bbca"]) == ["BBCA", "TLKM"]


def test_is_blocked_response_detects_cloudflare_html():
    response = FakeResponse(
        status_code=200,
        headers={"content-type": "text/html"},
        text="Attention Required! | Cloudflare",
    )
    assert is_blocked_response(response) is True


def test_metadata_store_uses_checksum_validation(monkeypatch):
    rows = [
        {
            "ticker": "BBCA",
            "year": "2023",
            "file_path": "data/reports/BBCA_2023.pdf",
            "status": "Success",
            "checksum": "abc123",
            "timestamp": "2026-05-05T00:00:00+00:00",
        }
    ]
    monkeypatch.setattr("webcrawler.core.read_csv_rows", lambda path: rows)
    monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
    monkeypatch.setattr("webcrawler.core.checksum_file", lambda path: "abc123")

    store = MetadataStore("data/metadata.csv")

    assert store.has_valid_download("BBCA", 2023) is True


def test_checksum_file_reads_sha256(monkeypatch):
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.BytesIO(b"annual-report-pdf"),
    )
    assert len(checksum_file("dummy.pdf")) == 64


def test_cli_returns_130_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr("webcrawler.cli.load_tickers_from_sources", lambda *args: ["BBCA"])
    monkeypatch.setattr("webcrawler.cli.parse_years", lambda years: [2023])
    def raise_interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("webcrawler.cli.run_crawl", raise_interrupt)
    assert main(["BBCA", "--years", "2023"]) == 130


def test_compatibility_exports_parse_cookie_header():
    from webcrawler.idx_reports import parse_cookie_header

    assert parse_cookie_header("cf_clearance=abc") == [
        {"name": "cf_clearance", "value": "abc", "domain": ".idx.co.id"}
    ]


def test_classify_exception_status_maps_cloudflare_and_404():
    assert classify_exception_status(IDXBlockedError("blocked")) == "Blocked_Cloudflare"
    assert classify_exception_status(IDXFileNotFoundError("missing")) == "File_Not_Found"


def test_classify_exception_status_maps_dns_errors():
    dns_error = RequestsConnectionError(
        "dns",
        NameResolutionError(None, "www.idx.co.id", socket.gaierror(11001, "getaddrinfo failed")),
    )
    assert classify_exception_status(dns_error) == "Failed_DNS"


def test_cli_smoke_flag_overrides_default_paths(monkeypatch):
    monkeypatch.setattr("webcrawler.cli.load_tickers_from_sources", lambda *args: ["BBCA"])
    monkeypatch.setattr("webcrawler.cli.parse_years", lambda years: [2023])

    captured = {}

    def fake_run_crawl(*args, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("webcrawler.cli.run_crawl", fake_run_crawl)

    assert main(["BBCA", "--years", "2023", "--smoke"]) == 0
    assert captured["metadata_path"] == "data/reports_smoke.csv"
    assert captured["reports_dir"] == "data/reports_smoke"

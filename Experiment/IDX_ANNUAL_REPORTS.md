# IDX Annual Report Crawler

Download annual report PDFs for public companies listed on IDX with a
sequential CLI, CSV metadata state, SHA-256 integrity checks, and a Playwright
fallback for blocked requests.

## Install

```bash
pip install -e .
python -m playwright install chromium
```

## Usage

```bash
# Download explicit tickers
idx-annual-reports BBCA TLKM --years 2023-2024

# Bulk tickers from file
idx-annual-reports --tickers-file tickers.txt --years 2020-2024

# Custom state paths
idx-annual-reports BBCA --years 2023 \
  --metadata-path data/metadata.csv \
  --reports-dir data/reports
```

The crawler writes PDFs to `data/reports/{ticker}_{year}.pdf` and maintains
state in `data/metadata.csv`.

The metadata CSV schema is:

```text
ticker,year,file_path,status,checksum,timestamp
```

`status` is one of:

```text
Success | Failed | Skipped | Blocked | Failed_DNS | Blocked_Cloudflare | File_Not_Found
```

Idempotency rules:

1. Before each download, the crawler checks the latest `ticker + year` row in
   `metadata.csv`.
2. If the file still exists on disk and its SHA-256 checksum matches the stored
   checksum, the run logs `Skipped`.
3. Otherwise the download is retried and the metadata row is rewritten by
   appending a new attempt.

## Transport flow

The CLI uses this order:

1. Reuse the `--cookie` value or `IDX_COOKIE` environment variable when present.
2. Otherwise try `requests` first.
3. On block or reset, launch a local Playwright Chromium session, open the IDX
   annual report page, and retry using the browser-backed network stack.

If you already have a working browser session, you can pass the cookie header
directly:

```bash
set IDX_COOKIE=cf_clearance=...; other_cookie=...
idx-annual-reports BBCA --years 2023
```

Disable automatic browser bootstrap with:

```bash
idx-annual-reports BBCA --years 2023 --no-browser-fallback
```

## Smoke mode

For operator testing without touching the main dataset:

```bash
idx-annual-reports BBCA TLKM --years 2023 --smoke
```

This writes to:

```text
data/reports_smoke.csv
data/reports_smoke/
```

## Local smoke run

```bash
idx-annual-reports BBCA TLKM --years 2023
```

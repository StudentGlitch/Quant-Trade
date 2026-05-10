import logging
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


logger = logging.getLogger("proof_collector")

GITHUB_PULL_PATTERN = re.compile(r'href="(/[^"/]+/[^"/]+/pull/\d+)"')


def _fetch_html(url: str, timeout: int = 20) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; micro-bounty-swarm/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def collect_github_proof_link(issue_url: str) -> str | None:
    """
    Read-only proof collector: finds a PR link referenced on the issue page.
    Returns first discovered absolute PR URL, otherwise None.
    """
    if "github.com" not in issue_url:
        return None
    try:
        html = _fetch_html(issue_url)
    except (URLError, HTTPError) as exc:
        logger.warning(f"Proof collection failed for {issue_url}: {exc}")
        return None
    except Exception as exc:
        logger.warning(f"Unexpected proof collection error for {issue_url}: {exc}")
        return None

    match = GITHUB_PULL_PATTERN.search(html)
    if not match:
        return None
    return f"https://github.com{match.group(1)}"

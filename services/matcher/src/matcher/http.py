"""Polite HTTP client for optional source adapters (docs/data-governance.md §2).

- Checks robots.txt before every request and never fetches a disallowed URL.
- Spaces requests to the same host (default 0.8 s) and backs off on 429/5xx.
- Sends an identifiable User-Agent with a contact URL.
- Never retries 401/403: an access refusal is respected, not worked around.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx2

USER_AGENT = "n8n-job-matching-agent/0.1 (+https://github.com/iramosv2000/n8n-job-matching-agent)"


class DisallowedByRobots(Exception):
    """The URL is disallowed for our User-Agent by the host's robots.txt."""


class PoliteClient:
    def __init__(
        self,
        *,
        min_interval: float = 0.8,
        timeout: float = 20.0,
        retries: int = 2,
        transport: httpx2.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = httpx2.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self.min_interval, self.retries = min_interval, retries
        self._sleep, self._clock = sleep, clock
        self._last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}
        self.robots_checked_at: dict[str, str] = {}
        self.requests = 0

    def _wait_turn(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            remaining = last + self.min_interval - self._clock()
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()

    def _robots_for(self, scheme: str, host: str) -> RobotFileParser:
        if host not in self._robots:
            parser = RobotFileParser()
            self._wait_turn(host)
            self.requests += 1
            try:
                response = self._client.get(f"{scheme}://{host}/robots.txt")
                status = response.status_code
                lines = response.text.splitlines() if status == 200 else []
            except httpx2.HTTPError:
                status, lines = 0, []
            if status == 200:
                parser.parse(lines)
            elif status in (404, 410):
                parser.allow_all = True  # no robots.txt: everything allowed
            else:
                parser.disallow_all = True  # unreadable or refused: assume nothing is allowed
            self._robots[host] = parser
            self.robots_checked_at[host] = datetime.now(UTC).isoformat(timespec="seconds")
        return self._robots[host]

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        return self._robots_for(parts.scheme, parts.netloc).can_fetch(USER_AGENT, url)

    def get_text(self, url: str) -> str | None:
        """Body of a 200 response; None for 404/410 or an access refusal; raises DisallowedByRobots."""
        if not self.allowed(url):
            raise DisallowedByRobots(url)
        host = urlsplit(url).netloc
        for attempt in range(self.retries + 1):
            self._wait_turn(host)
            self.requests += 1
            try:
                response = self._client.get(url)
            except httpx2.HTTPError:
                response = None
            if response is not None:
                if response.status_code == 200:
                    return response.text
                if response.status_code in (401, 403, 404, 410):
                    return None
            if attempt < self.retries:
                self._sleep(3.0 * (attempt + 1))  # 429, 5xx or network error: back off
        return None

    def close(self) -> None:
        self._client.close()

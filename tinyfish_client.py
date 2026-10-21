"""
NiyamAI - TinyFish API Client
Official integration client for TinyFish Search API and Fetch API.
Specification compliance:
- Search: GET https://api.search.tinyfish.ai (Headers: X-API-Key)
- Fetch: POST https://api.fetch.tinyfish.ai (Headers: X-API-Key, Content-Type: application/json)
Includes SSRF validation, comprehensive status codes, rate-limit backoff, and typed models.
"""

import time
import logging
from typing import List, Optional, Dict, Any
import requests

from config import (
    TINYFISH_API_KEY,
    TINYFISH_SEARCH_ENDPOINT,
    TINYFISH_FETCH_ENDPOINT,
    TINYFISH_LOCATION,
    TINYFISH_LANGUAGE,
    is_safe_url,
)
from models import (
    SearchResponse,
    SearchResultItem,
    FetchResponse,
    FetchResponseItem,
    FetchErrorItem,
)

logger = logging.getLogger("niyamai.tinyfish")


class TinyFishError(Exception):
    """Base exception for TinyFish API interactions."""
    def __init__(self, message: str, status_code: Optional[int] = None, code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class TinyFishAuthError(TinyFishError):
    """Raised when API key is missing, invalid, or unauthorized (401)."""
    pass


class TinyFishCreditsError(TinyFishError):
    """Raised when daily allowance is exhausted or wallet needs top-up (402)."""
    pass


class TinyFishRateLimitError(TinyFishError):
    """Raised when rate limit is exceeded (429)."""
    pass


class TinyFishClient:
    """
    Client for interacting with TinyFish Search and Fetch APIs.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 150):
        # Explicit empty string means "no key" - don't fall back to config
        if api_key == "":
            self.api_key = ""
        else:
            self.api_key = (api_key or TINYFISH_API_KEY).strip()
        self.timeout = timeout  # 150s recommended by TinyFish documentation

    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key and len(self.api_key) > 5)

    def _get_headers(self) -> Dict[str, str]:
        """Constructs authentication and request headers."""
        if not self.is_configured():
            raise TinyFishAuthError(
                "TinyFish API key is not configured. Please supply a valid TINYFISH_API_KEY in .env or via dashboard settings.",
                status_code=401,
                code="API_KEY_MISSING",
            )
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "NiyamAI/1.0",
        }

    def search(
        self,
        query: str,
        purpose: Optional[str] = None,
        location: Optional[str] = None,
        language: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        page: int = 0,
        max_retries: int = 2,
    ) -> SearchResponse:
        """
        Executes a live search via TinyFish Search API.
        Endpoint: GET https://api.search.tinyfish.ai
        """
        if not query or not query.strip():
            raise TinyFishError("Search query cannot be empty.", status_code=400, code="EMPTY_QUERY")

        headers = self._get_headers()
        params: Dict[str, Any] = {
            "query": query.strip(),
            "location": location or TINYFISH_LOCATION or "IN",
            "language": language or TINYFISH_LANGUAGE or "en",
            "page": min(max(0, page), 10),
        }

        if purpose:
            params["purpose"] = purpose[:2000]

        if include_domains:
            # Clean and comma-separate domains
            cleaned = [d.strip().lower() for d in include_domains if d.strip()]
            if cleaned:
                params["include_domains"] = ",".join(cleaned)

        if exclude_domains:
            cleaned = [d.strip().lower() for d in exclude_domains if d.strip()]
            if cleaned:
                params["exclude_domains"] = ",".join(cleaned)

        # Execute GET request with retry backoff for rate limits or transient errors
        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(
                    TINYFISH_SEARCH_ENDPOINT,
                    headers={"X-API-Key": self.api_key, "User-Agent": "NiyamAI/1.0"},
                    params=params,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for idx, r in enumerate(data.get("results", [])):
                        results.append(
                            SearchResultItem(
                                position=r.get("position", idx + 1),
                                site_name=r.get("site_name") or "",
                                title=r.get("title") or "Untitled Notice",
                                snippet=r.get("snippet") or "",
                                url=r.get("url") or "",
                                date=r.get("date"),
                            )
                        )
                    return SearchResponse(
                        query=data.get("query", query),
                        results=results,
                        total_results=data.get("total_results", len(results)),
                        page=data.get("page", page),
                    )

                if resp.status_code == 401:
                    raise TinyFishAuthError(
                        "TinyFish Authentication Failed (HTTP 401). Please check that your TINYFISH_API_KEY is valid.",
                        status_code=401,
                        code="INVALID_API_KEY",
                    )
                elif resp.status_code == 402:
                    raise TinyFishCreditsError(
                        "TinyFish Credits Exhausted (HTTP 402). Your daily free allowance is used or wallet balance is zero.",
                        status_code=402,
                        code="INSUFFICIENT_CREDITS",
                    )
                elif resp.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    raise TinyFishRateLimitError(
                        "TinyFish Search Rate Limit Exceeded (HTTP 429). Please wait a moment before retrying.",
                        status_code=429,
                        code="RATE_LIMIT_EXCEEDED",
                    )
                elif resp.status_code == 400:
                    raise TinyFishError(
                        f"TinyFish Search Bad Request (HTTP 400): {resp.text}",
                        status_code=400,
                        code="BAD_REQUEST",
                    )
                else:
                    raise TinyFishError(
                        f"TinyFish Search API Error (HTTP {resp.status_code}): {resp.text}",
                        status_code=resp.status_code,
                    )

            except requests.Timeout as e:
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                raise TinyFishError("TinyFish Search request timed out.", status_code=504, code="TIMEOUT") from e
            except requests.RequestException as e:
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                raise TinyFishError(f"Network error communicating with TinyFish Search: {e}") from e

        raise TinyFishError("Search failed after retries.")

    def fetch(
        self,
        urls: List[str],
        purpose: Optional[str] = None,
        format: str = "markdown",
        max_retries: int = 1,
    ) -> FetchResponse:
        """
        Fetches web page contents via TinyFish Fetch API.
        Endpoint: POST https://api.fetch.tinyfish.ai
        Validates URLs for SSRF safety before issuing requests.
        """
        if not urls:
            return FetchResponse(results=[], errors=[])

        # Security check: SSRF defense
        safe_urls = []
        errors = []
        for u in urls[:10]:  # TinyFish allows max 10 URLs per batch
            if is_safe_url(u):
                safe_urls.append(u)
            else:
                errors.append(
                    FetchErrorItem(
                        url=u,
                        error="invalid_url_blocked_for_security (Localhost or private network forbidden)",
                        status=400,
                    )
                )

        if not safe_urls:
            return FetchResponse(results=[], errors=errors)

        headers = self._get_headers()
        payload: Dict[str, Any] = {
            "urls": safe_urls,
            "format": format,
        }
        if purpose:
            payload["purpose"] = purpose[:2000]

        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(
                    TINYFISH_FETCH_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for r in data.get("results", []):
                        results.append(
                            FetchResponseItem(
                                url=r.get("url") or "",
                                final_url=r.get("final_url"),
                                title=r.get("title"),
                                description=r.get("description"),
                                language=r.get("language"),
                                author=r.get("author"),
                                published_date=r.get("published_date"),
                                text=r.get("text") or "",
                                format=r.get("format", format),
                                latency_ms=r.get("latency_ms"),
                            )
                        )
                    for err in data.get("errors", []):
                        errors.append(
                            FetchErrorItem(
                                url=err.get("url") or "",
                                error=err.get("error") or "Unknown error",
                                status=err.get("status"),
                            )
                        )
                    return FetchResponse(results=results, errors=errors)

                if resp.status_code == 401:
                    raise TinyFishAuthError(
                        "TinyFish Authentication Failed (HTTP 401). Check TINYFISH_API_KEY.",
                        status_code=401,
                        code="INVALID_API_KEY",
                    )
                elif resp.status_code == 402:
                    raise TinyFishCreditsError(
                        "TinyFish Credits Exhausted (HTTP 402). Daily limit reached or wallet balance zero.",
                        status_code=402,
                        code="INSUFFICIENT_CREDITS",
                    )
                elif resp.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(2.0)
                        continue
                    raise TinyFishRateLimitError(
                        "TinyFish Fetch Rate Limit Exceeded (HTTP 429).",
                        status_code=429,
                        code="RATE_LIMIT_EXCEEDED",
                    )
                else:
                    raise TinyFishError(
                        f"TinyFish Fetch API Error (HTTP {resp.status_code}): {resp.text}",
                        status_code=resp.status_code,
                    )

            except requests.Timeout as e:
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                raise TinyFishError("TinyFish Fetch request timed out.", status_code=504, code="TIMEOUT") from e
            except requests.RequestException as e:
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                raise TinyFishError(f"Network error communicating with TinyFish Fetch: {e}") from e

        return FetchResponse(results=[], errors=errors)

    def fetch_single(self, url: str, purpose: Optional[str] = None) -> FetchResponseItem:
        """Convenience method to fetch a single URL and return content directly."""
        resp = self.fetch(urls=[url], purpose=purpose)
        if resp.results:
            return resp.results[0]
        if resp.errors:
            err = resp.errors[0]
            raise TinyFishError(f"Failed to fetch {url}: {err.error} (Status: {err.status})")
        raise TinyFishError(f"No result or error returned for {url}")

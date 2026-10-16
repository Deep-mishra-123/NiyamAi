"""
Unit tests for TinyFishClient covering Search and Fetch API calls,
authentication failures, rate limiting, and SSRF security defense.
"""

from unittest.mock import patch, MagicMock
import pytest
import requests

from tinyfish_client import (
    TinyFishClient,
    TinyFishAuthError,
    TinyFishRateLimitError,
    TinyFishError,
)
from tests.conftest import (
    SAMPLE_SEARCH_RESPONSE_JSON,
    SAMPLE_FETCH_SUCCESS_JSON,
    SAMPLE_FETCH_FAILURE_JSON,
)


def test_unconfigured_client_raises_auth_error():
    """Client without API key raises TinyFishAuthError."""
    client = TinyFishClient(api_key="")
    assert not client.is_configured()
    with pytest.raises(TinyFishAuthError):
        client.search(query="test query")


@patch("requests.get")
def test_search_success(mock_get):
    """Successful search returns parsed SearchResponse model."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_SEARCH_RESPONSE_JSON
    mock_get.return_value = mock_resp

    client = TinyFishClient(api_key="tf_live_test_key_12345")
    res = client.search(
        query="solar rooftop tender",
        location="IN",
        include_domains=["gem.gov.in", "eprocure.gov.in"],
    )

    assert res.total_results == 2
    assert len(res.results) == 2
    assert res.results[0].site_name == "gem.gov.in"
    assert "Supply and Installation" in res.results[0].title
    assert mock_get.called
    # Check headers
    args, kwargs = mock_get.call_args
    assert kwargs["headers"]["X-API-Key"] == "tf_live_test_key_12345"


@patch("requests.get")
def test_search_401_auth_failure(mock_get):
    """HTTP 401 returns TinyFishAuthError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "Unauthorized"}'
    mock_get.return_value = mock_resp

    client = TinyFishClient(api_key="invalid_key")
    with pytest.raises(TinyFishAuthError) as exc_info:
        client.search(query="tenders")
    assert "HTTP 401" in str(exc_info.value)


@patch("requests.get")
def test_search_429_rate_limit(mock_get):
    """HTTP 429 raises TinyFishRateLimitError after retries."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = '{"error": "Rate limit exceeded"}'
    mock_get.return_value = mock_resp

    client = TinyFishClient(api_key="valid_key")
    with pytest.raises(TinyFishRateLimitError):
        client.search(query="tenders", max_retries=0)


@patch("requests.get")
def test_search_timeout(mock_get):
    """Timeout during search raises TinyFishError with code TIMEOUT."""
    mock_get.side_effect = requests.Timeout("Connection timed out")
    client = TinyFishClient(api_key="valid_key")
    with pytest.raises(TinyFishError) as exc:
        client.search(query="tenders", max_retries=0)
    assert "timed out" in str(exc.value)


@patch("requests.post")
def test_fetch_success(mock_post):
    """Successful fetch returns markdown content in FetchResponse."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_FETCH_SUCCESS_JSON
    mock_post.return_value = mock_resp

    client = TinyFishClient(api_key="valid_key")
    resp = client.fetch(urls=["https://gem.gov.in/tenders/solar-pv-98712"])

    assert len(resp.results) == 1
    assert len(resp.errors) == 0
    assert "Supply and Installation" in resp.results[0].title
    assert "Bid Submission Date" in resp.results[0].text


@patch("requests.post")
def test_fetch_per_url_failure(mock_post):
    """Fetch endpoint returning per-URL failure in errors[] is handled gracefully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_FETCH_FAILURE_JSON
    mock_post.return_value = mock_resp

    client = TinyFishClient(api_key="valid_key")
    resp = client.fetch(urls=["https://gem.gov.in/broken-notice"])

    assert len(resp.results) == 0
    assert len(resp.errors) == 1
    assert resp.errors[0].error == "page_not_found"
    assert resp.errors[0].status == 404


def test_fetch_ssrf_protection():
    """Client rejects localhost and AWS/GCP metadata endpoints before sending network requests."""
    client = TinyFishClient(api_key="valid_key")
    unsafe_urls = [
        "http://localhost:8000/admin",
        "http://127.0.0.1/secrets",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file",
    ]

    resp = client.fetch(urls=unsafe_urls)
    assert len(resp.results) == 0
    assert len(resp.errors) == len(unsafe_urls)
    for err in resp.errors:
        assert "blocked_for_security" in err.error

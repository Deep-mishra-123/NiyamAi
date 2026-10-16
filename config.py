"""
NiyamAI - Configuration & Security Validation
Handles environment loading, application settings, and SSRF security checks.
"""

import os
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# TinyFish API Configuration
TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY", "").strip()
TINYFISH_SEARCH_ENDPOINT = "https://api.search.tinyfish.ai"
TINYFISH_FETCH_ENDPOINT = "https://api.fetch.tinyfish.ai"
TINYFISH_LOCATION = os.getenv("TINYFISH_LOCATION", "IN").strip()
TINYFISH_LANGUAGE = os.getenv("TINYFISH_LANGUAGE", "en").strip()

# Gemini LLM Configuration (Optional)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# SQLite Database
DEFAULT_DB_PATH = str(BASE_DIR / "niyamai.db")
NIYAMAI_DB_PATH = os.getenv("NIYAMAI_DB_PATH", DEFAULT_DB_PATH).strip()

# Trusted Indian Government & Procurement Domains
DEFAULT_GOV_DOMAINS = [
    "gem.gov.in",
    "eprocure.gov.in",
    "msme.gov.in",
    "startupindia.gov.in",
    "sidbi.in",
    "mygov.in",
    "nsic.co.in",
    "dst.gov.in",
    "meity.gov.in",
    "mptrds.gov.in",
    "mahatenders.gov.in",
    "kppp.karnataka.gov.in",
    "tn.tenders.gov.in",
]

# Security: Forbidden Hostnames & IP Ranges (SSRF Defense)
DISALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "169.254.169.254",  # Cloud metadata IP
}


def is_safe_url(url: str) -> bool:
    """
    Validates whether a URL is safe to fetch via TinyFish Fetch API.
    Prevents SSRF attacks to localhost, private networks, and metadata endpoints.
    """
    if not url or not isinstance(url, str):
        return False

    url_clean = url.strip()
    try:
        parsed = urlparse(url_clean)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        if hostname_lower in DISALLOWED_HOSTS:
            return False

        # Check for private or loopback IP addresses
        try:
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            # Not an IP address, domain name is fine unless localhost/internal
            pass

        if hostname_lower.endswith(".internal") or hostname_lower.endswith(".local"):
            return False

        return True
    except Exception:
        return False

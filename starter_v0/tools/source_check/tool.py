from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _domain_from_url_or_domain(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    if not parsed.netloc and parsed.path:
        parsed = urlparse(f"//{value}")
    domain = (parsed.netloc or parsed.path).lower().removeprefix("www.")
    return domain, parsed.scheme.lower()


def check_source(url: str = "") -> dict[str, Any]:
    value = (url or "").strip()
    domain, scheme = _domain_from_url_or_domain(value)

    if not value or not domain:
        return {
            "tool": "source_check",
            "error": "missing_url",
            "message": "Provide a URL or domain to check.",
            "url": value,
        }

    known_primary = {
        "openai.com",
        "anthropic.com",
        "deepmind.google",
        "ai.googleblog.com",
        "microsoft.com",
        "arxiv.org",
        "nature.com",
        "science.org",
    }
    known_news = {
        "reuters.com",
        "apnews.com",
        "theverge.com",
        "techcrunch.com",
        "wired.com",
        "bloomberg.com",
    }

    if domain in known_primary or domain.endswith(".edu") or domain.endswith(".gov"):
        source_type = "primary_or_authoritative"
        risk_level = "low"
        advice = "Good candidate for citation. Fetch the page before summarizing details."
    elif domain in known_news:
        source_type = "news_or_industry_media"
        risk_level = "medium"
        advice = "Usable for news context. Cross-check important claims with a primary source when possible."
    else:
        source_type = "unknown_or_unclassified"
        risk_level = "medium"
        advice = "Use cautiously. Prefer fetching the page and comparing with another source before citing."

    return {
        "tool": "source_check",
        "url": value,
        "domain": domain,
        "is_https": scheme == "https",
        "source_type": source_type,
        "risk_level": risk_level,
        "citation_advice": advice,
    }

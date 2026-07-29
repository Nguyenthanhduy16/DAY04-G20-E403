from __future__ import annotations

from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


ENDPOINTS = {
    "relevance": "https://hn.algolia.com/api/v1/search",
    "recent": "https://hn.algolia.com/api/v1/search_by_date",
}
MAX_LIMIT = 20


def search_hackernews(
    query: str = "",
    sort_by: str = "relevance",
    limit: int = 5,
    min_points: int = 0,
) -> dict[str, Any]:
    """Search Hacker News stories through the public Algolia index. No API key."""
    try:
        if not query.strip():
            raise ValueError("query must not be empty")
        endpoint = ENDPOINTS.get(sort_by)
        if endpoint is None:
            raise ValueError(f"sort_by must be one of {sorted(ENDPOINTS)}, got {sort_by!r}")

        limit = max(1, min(int(limit or 5), MAX_LIMIT))
        params: dict[str, Any] = {"query": query, "tags": "story", "hitsPerPage": limit}
        min_points = int(min_points or 0)
        if min_points > 0:
            params["numericFilters"] = f"points>={min_points}"

        response = requests.get(endpoint, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        hits = response.json().get("hits", [])

        items: list[dict[str, Any]] = []
        for hit in hits:
            story_id = hit.get("objectID")
            discussion_url = f"https://news.ycombinator.com/item?id={story_id}"
            story_url = hit.get("url") or discussion_url
            points = hit.get("points") or 0
            comments = hit.get("num_comments") or 0
            items.append({
                "title": hit.get("title"),
                "url": story_url,
                "source": domain(story_url) or "news.ycombinator.com",
                "summary": f"{points} points, {comments} comments on Hacker News",
                "points": points,
                "num_comments": comments,
                "author": hit.get("author"),
                "created_at": hit.get("created_at"),
                "discussion_url": discussion_url,
            })

        return {
            "tool": "hn_search",
            "query": query,
            "sort_by": sort_by,
            "min_points": min_points,
            "item_count": len(items),
            "items": items,
        }
    except Exception as exc:
        return err("hn_search", exc)

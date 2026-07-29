# source_check

## Purpose

Check a URL or domain before using it as a cited source. The tool classifies common primary, academic, government, and news domains and returns a short citation-risk recommendation.

## When to use

Use `source_check` when the user asks whether a URL/source/domain is suitable, trustworthy enough to cite, or should be checked before inclusion in a research digest.

Do not use it to read article contents. If the user asks to summarize a URL, use `fetch`.

## Arguments

- `url` string, required: URL or domain to check.

## Returns

A dictionary with `domain`, `is_https`, `source_type`, `risk_level`, and `citation_advice`.

"""Canonical source registry for the daily current-affairs pipeline.

Single source of truth for every RSS source consumed by collection stages.

Design rules (Task 01):
- Reuses existing Python registries (config.feeds.VERIFIED_RSS and
  config.sources.ALL_SOURCES). No URL is duplicated here.
- No ``sources.json`` compatibility shim: if a JSON file ever appears it is
  ignored on purpose so two divergent lists can never coexist silently.
- Fail-loud: malformed or empty configuration raises SourceConfigError with an
  actionable message instead of producing an empty edition.
- No circular imports: this module imports only stdlib + config modules;
  nothing inside config/ imports this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class SourceConfigError(RuntimeError):
    """Raised when the canonical source configuration is unusable."""


@dataclass(frozen=True)
class SourceSpec:
    """One validated RSS source entry."""

    source_id: str
    name: str
    rss_url: str
    tier: int = 2
    category: str = "general"
    official: bool = False
    language: str = "en"
    enabled: bool = True
    verification_policy: str = "corroborate"
    extra: dict = field(default_factory=dict)


def _valid_http_url(url: object) -> bool:
    return isinstance(url, str) and bool(_URL_RE.match(url.strip()))


def _load_verified_rss() -> List[SourceSpec]:
    """Load VERIFIED_RSS from config/feeds.py (primary curated list)."""
    try:
        from config.feeds import VERIFIED_RSS
    except ImportError as exc:  # pragma: no cover - packaging issue
        raise SourceConfigError(
            f"Cannot import config.feeds.VERIFIED_RSS: {exc}"
        ) from exc

    if not isinstance(VERIFIED_RSS, list) or not VERIFIED_RSS:
        raise SourceConfigError(
            "config.feeds.VERIFIED_RSS is missing or empty; refusing to run "
            "collection with zero sources."
        )

    specs: List[SourceSpec] = []
    problems: List[str] = []
    for idx, entry in enumerate(VERIFIED_RSS):
        where = f"VERIFIED_RSS[{idx}]"
        if isinstance(entry, (tuple, list)) and len(entry) == 4:
            name, rss, tier, category = entry
            entry = {"name": name, "rss": rss, "tier": tier, "category": category}
        if not isinstance(entry, dict):
            problems.append(f"{where}: expected dict or four-field tuple, got {type(entry).__name__}")
            continue
        name = str(entry.get("name") or "").strip()
        rss = str(entry.get("rss") or "").strip()
        if not name:
            problems.append(f"{where}: missing 'name'")
            continue
        if not _valid_http_url(rss):
            problems.append(f"{where} ({name}): invalid or missing 'rss' URL: {rss!r}")
            continue
        try:
            tier = int(str(entry.get("tier", 2)).removeprefix("tier"))
            if tier not in {1, 2, 3}:
                raise ValueError("tier outside 1..3")
        except (ValueError, TypeError):
            problems.append(f"{where}: invalid tier {entry.get('tier')!r}")
            continue
        specs.append(
            SourceSpec(
                source_id=f"feed-{idx:02d}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}",
                name=name,
                rss_url=rss.strip(),
                tier=tier,
                category=str(entry.get("category", "general")),
                official=bool(entry.get("official", tier == 1)),
                language=str(entry.get("language", "en")),
                enabled=bool(entry.get("enabled", True)),
                verification_policy=str(entry.get("verification_policy", "corroborate")),
                extra={k: v for k, v in entry.items()
                       if k not in {"name", "rss", "tier", "category", "official",
                                    "language", "enabled", "verification_policy"}},
            )
        )
    if problems:
        raise SourceConfigError(
            "Malformed source configuration in config.feeds.VERIFIED_RSS:\n  - "
            + "\n  - ".join(problems)
        )
    if not specs:
        raise SourceConfigError(
            "config.feeds.VERIFIED_RSS contained no usable entries."
        )
    return specs


def _load_all_sources(specs: List[SourceSpec]) -> None:
    """Merge ALL_SOURCES from config/sources.py into the registry in place.

    Entries already present (matched by RSS URL) are skipped so the same feed
    is never fetched twice. Sources without an ``rss`` key are skipped with a
    note — they cannot be fetched by an RSS collector and must not be
    silently counted as live sources.
    """
    try:
        from config.sources import ALL_SOURCES
    except ImportError as exc:  # pragma: no cover - packaging issue
        raise SourceConfigError(
            f"Cannot import config.sources.ALL_SOURCES: {exc}"
        ) from exc

    if not isinstance(ALL_SOURCES, (list, tuple)):
        raise SourceConfigError(
            "config.sources.ALL_SOURCES must be a list of source dicts; "
            f"got {type(ALL_SOURCES).__name__}."
        )

    seen_urls = {s.rss_url for s in specs}
    problems: List[str] = []
    for idx, entry in enumerate(ALL_SOURCES):
        where = f"ALL_SOURCES[{idx}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: expected dict, got {type(entry).__name__}")
            continue
        name = str(entry.get("name") or entry.get("id") or "").strip()
        rss = str(entry.get("rss") or "").strip()
        if not rss:
            continue  # non-RSS source definition; out of scope for RSS collector
        if not _valid_http_url(rss):
            problems.append(f"{where} ({name}): invalid 'rss' URL: {rss!r}")
            continue
        if rss in seen_urls:
            continue  # already covered by VERIFIED_RSS — do not duplicate fetches
        seen_urls.add(rss)
        level = entry.get("level")
        inferred = 1 if isinstance(level, int) and level <= 3 else 2 if level == 4 else 3
        tier_raw = entry.get("tier", inferred)
        try:
            tier = int(str(tier_raw).removeprefix("tier"))
            if tier not in {1, 2, 3}:
                raise ValueError("invalid tier")
        except (TypeError, ValueError):
            problems.append(f"{where}: invalid tier {tier_raw!r}")
            continue
        publisher_host = urlparse(entry.get("url", "")).hostname
        feed_host = urlparse(rss).hostname
        direct = bool(publisher_host and feed_host and (feed_host == publisher_host or feed_host.endswith("." + publisher_host)))
        specs.append(
            SourceSpec(
                source_id=str(entry.get("id") or f"src-{idx:02d}"),
                name=name or str(entry.get("id") or f"src-{idx:02d}"),
                rss_url=rss,
                tier=tier,
                category=str(entry.get("category", "general")),
                official=bool(entry.get("official", tier == 1 and direct)),
                language=str(entry.get("language", "en")),
                enabled=bool(entry.get("enabled", True)),
                verification_policy=str(entry.get("verification_policy", "corroborate")),
                extra={k: v for k, v in entry.items()
                       if k not in {"id", "name", "rss", "tier", "category", "official",
                                    "language", "enabled", "verification_policy"}},
            )
        )
    if problems:
        raise SourceConfigError(
            "Malformed source configuration in config.sources.ALL_SOURCES:\n  - "
            + "\n  - ".join(problems)
        )


def load_sources() -> List[SourceSpec]:
    """Return the validated canonical list of enabled RSS sources.

    Raises:
        SourceConfigError: if either registry is missing, empty or malformed.
    """
    specs = _load_verified_rss()
    _load_all_sources(specs)
    enabled = [s for s in specs if s.enabled]
    if not enabled:
        raise SourceConfigError(
            "All configured sources are disabled; refusing to run collection."
        )
    return enabled


def registry_summary() -> dict:
    """Small introspection payload used by logs/tests (no network access)."""
    specs = load_sources()
    tiers: dict = {}
    categories: dict = {}
    for s in specs:
        tiers[s.tier] = tiers.get(s.tier, 0) + 1
        categories[s.category] = categories.get(s.category, 0) + 1
    return {
        "count": len(specs),
        "by_tier": tiers,
        "by_category": categories,
        "source_ids": sorted(s.source_id for s in specs),
    }

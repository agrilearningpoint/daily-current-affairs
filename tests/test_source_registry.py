import config.sources as s


def test_levels():
    levels = [s.LEVEL_0_CORE, s.LEVEL_1_AGRI, s.LEVEL_2_FINANCE,
              s.LEVEL_3_GOVT, s.LEVEL_4_DISCOVERY, s.LEVEL_5_FALLBACK]
    assert s.ALL_SOURCES == [src for group in levels for src in group]
    assert all(levels)
    assert s.PRIORITY_MAP[0] == 100
    assert s.PRIORITY_MAP[0] > s.PRIORITY_MAP[5]
    for level, group in enumerate(levels):
        for src in group:
            assert src["level"] == level
            assert 0 < src["priority"] <= 100
            assert src["frequency"] and "verification_required" in src


def test_no_equal_priority_all():
    assert min(x["priority"] for x in s.LEVEL_0_CORE) > max(x["priority"] for x in s.LEVEL_5_FALLBACK)


# ---------------------------------------------------------------------------
# Canonical merged registry invariants (pipeline.source_registry combines
# config.feeds.VERIFIED_RSS with config.sources.ALL_SOURCES).
# ---------------------------------------------------------------------------
def _rss_host(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(str(url or "")).hostname or "").lower()


def test_verified_rss_and_all_sources_agree_on_shared_publishers():
    """The same publisher must not be configured with two different RSS URLs.

    pipeline.source_registry dedupes by exact RSS URL. If VERIFIED_RSS and
    ALL_SOURCES list the same publisher with *different* URLs, the collector
    fetches the same organisation twice (duplicate stories, wasted budget).
    """
    from config.feeds import VERIFIED_RSS
    from config.sources import ALL_SOURCES

    all_by_host: dict[str, list[str]] = {}
    for src in ALL_SOURCES:
        url = str(src.get("rss") or "")
        if url.startswith("http"):
            all_by_host.setdefault(_rss_host(url), []).append(url)

    conflicts: list[str] = []
    for entry in VERIFIED_RSS:
        name, rss = entry[0], entry[1]
        for peer in all_by_host.get(_rss_host(rss), []):
            if peer.rstrip("/") != str(rss).rstrip("/"):
                conflicts.append(
                    f"{name}: VERIFIED_RSS {rss!r} != ALL_SOURCES {peer!r}"
                )
    assert not conflicts, "duplicate publisher with conflicting feed URLs:\n  - " + "\n  - ".join(conflicts)


def test_canonical_registry_loads_and_has_no_duplicate_rss_urls():
    from pipeline.source_registry import load_sources, registry_summary

    specs = load_sources()
    assert specs, "canonical registry must not be empty"
    urls = [spec.rss_url for spec in specs]
    assert len(urls) == len(set(urls)), (
        "canonical registry would fetch the same RSS URL twice: "
        + repr(sorted({u for u in urls if urls.count(u) > 1}))
    )
    summary = registry_summary()
    assert summary["count"] == len(specs)
    assert summary["count"] > 0
    assert all(spec.enabled for spec in specs)


def test_canonical_registry_has_core_exam_category_coverage():
    """Guard against silently dropping whole exam-relevant categories."""
    from pipeline.source_registry import load_sources

    specs = load_sources()
    categories = {spec.category.lower() for spec in specs}
    # Core exam-relevant coverage must remain present after any registry edit.
    for required in ("agriculture_core", "banking_finance", "national"):
        assert required in categories or any(
            required.split("_")[0] in c for c in categories
        ), f"category coverage lost: {required!r} (have {sorted(categories)})"

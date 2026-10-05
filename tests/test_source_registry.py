import config.sources as s
def test_levels():
    assert len(s.ALL_SOURCES)==69, f"expected 69 got {len(s.ALL_SOURCES)}"
    assert len(s.LEVEL_0_CORE)==20
    assert len(s.LEVEL_4_DISCOVERY)==6
    assert s.PRIORITY_MAP[0]==100 and s.PRIORITY_MAP[5]==60
    for src in s.ALL_SOURCES:
        assert "level" in src and "priority" in src and "frequency" in src
        assert "verification_required" in src
def test_no_equal_priority_all():
    # CORE must be higher than FALLBACK
    assert max(x["priority"] for x in s.LEVEL_0_CORE) > max(x["priority"] for x in s.LEVEL_5_FALLBACK)

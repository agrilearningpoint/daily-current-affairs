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

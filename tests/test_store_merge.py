from pipeline.store import _merge_dicts
def test_merge_newer_wins():
    local={"a":{"last_seen":"2026-10-06"}}
    remote={"a":{"last_seen":"2026-10-05"},"b":{"last_seen":"2026-10-06"}}
    merged=_merge_dicts(local,remote)
    assert "a" in merged and "b" in merged
    assert merged["a"]["last_seen"]=="2026-10-06"

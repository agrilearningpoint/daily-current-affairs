import json

from pipeline import content


def test_headline_batch_prefills_cache_with_one_router_call(monkeypatch):
    from pipeline import ai_router

    content._TRANSLATION_CACHE.clear()
    calls = []

    def fake_route(prompt, **kwargs):
        calls.append((json.loads(prompt), kwargs))
        return json.dumps({"translations": ["कृषि योजना को मंत्रिमंडल की मंजूरी"]})

    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "route", fake_route)

    count = content._prefill_headline_translation_cache([{
        "headline_en": "Cabinet Approves New Agriculture Scheme for Farmers",
        "raw_facts": "The scheme supports farmers.",
    }])

    assert count == 1
    assert len(calls) == 1
    assert calls[0][1]["task"] == "bilingual_headline_batch"
    assert content._TRANSLATION_CACHE[("headline", "Cabinet Approves New Agriculture Scheme for Farmers")][0].startswith("कृषि")


def test_headline_batch_rejects_non_hindi_values(monkeypatch):
    from pipeline import ai_router

    content._TRANSLATION_CACHE.clear()
    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(
        ai_router, "route",
        lambda *_args, **_kwargs: '{"translations": ["English only headline"]}',
    )

    count = content._prefill_headline_translation_cache([{
        "headline_en": "Cabinet Approves New Agriculture Scheme for Farmers",
        "raw_facts": "The scheme supports farmers.",
    }])

    assert count == 0
    assert not content._TRANSLATION_CACHE

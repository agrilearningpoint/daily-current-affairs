# -*- coding: utf-8 -*-
"""Regression tests for format steps 4-10 (reference Exam Genius layout)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SRC = ("The Union Cabinet approved a ₹1,250 crore scheme to modernise 500 primary agricultural "
       "credit societies. NABARD will be the implementing agency.")


def _llm_json(**over):
    data = {
        "mcq": {
            "question": {"en": "Which agency will implement the PACS modernisation scheme approved by the Cabinet?",
                         "hi": "मंत्रिमंडल द्वारा स्वीकृत पैक्स आधुनिकीकरण योजना को कौन सी एजेंसी लागू करेगी?"},
            "options": [{"en": "SIDBI", "hi": "सिडबी"}, {"en": "NABARD", "hi": "नाबार्ड"},
                        {"en": "EXIM Bank", "hi": "एक्ज़िम बैंक"}, {"en": "SEBI", "hi": "सेबी"},
                        {"en": "IFCI", "hi": "आईएफसीआई"}],
            "correct": "B",
        },
        "explanation": [{"en": f"Sentence {i} about NABARD.", "hi": f"नाबार्ड के बारे में वाक्य {i}।"} for i in range(1, 5)],
        "static_gk": [{"label_en": l, "value_en": v, "label_hi": lh, "value_hi": vh} for l, v, lh, vh in [
            ("Institution", "NABARD", "संस्था", "नाबार्ड"), ("Established", "12 July 1982", "स्थापना", "12 जुलाई 1982"),
            ("Headquarters", "Mumbai", "मुख्यालय", "मुंबई"), ("Parent", "Ministry of Finance", "मूल", "वित्त मंत्रालय")]],
        "theme": "Agriculture",
        "one_liner": {"en": "NABARD will implement the ₹1,250 crore PACS scheme.", "hi": "नाबार्ड ₹1,250 करोड़ की पैक्स योजना लागू करेगा।"},
    }
    data.update(over)
    return data


# --- Step 5: LLM per-item JSON schema --------------------------------------
def test_schema_normalises_and_validates():
    from pipeline.mcq_schema import normalize_item_mcq, parse_llm_json, schema_errors
    raw = "```json\n" + json.dumps(_llm_json(), ensure_ascii=False) + "\n```"
    m = normalize_item_mcq(parse_llm_json(raw), {"event_id": "e1"})
    assert m["options"][1] == "NABARD" and m["options_hi"][1] == "नाबार्ड"
    assert len(m["explanation_pairs"]) == 4 and len(m["static_gk"]) == 4
    assert schema_errors(m, SRC) == []


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d["mcq"]["options"].__setitem__(4, {"en": "None of the above", "hi": "उपर्युक्त में से कोई नहीं"}), "None/All"),
    (lambda d: d["mcq"]["options"].pop(), "exactly 5"),
    (lambda d: d["mcq"]["options"][0].__setitem__("hi", ""), "Hindi text missing"),
    (lambda d: d["mcq"].__setitem__("correct", "C"), "not found in source"),
    (lambda d: d.__setitem__("explanation", d["explanation"][:2]), "4-5 sentences"),
    (lambda d: d["mcq"]["question"].__setitem__("hi", ""), "Hindi question"),
])
def test_schema_rejects_bad_mcqs(mutate, expected):
    from pipeline.mcq_schema import normalize_item_mcq, schema_errors
    data = _llm_json()
    mutate(data)
    errs = schema_errors(normalize_item_mcq(data, {"event_id": "e1"}), SRC)
    assert any(expected in e for e in errs), errs


def test_generate_llm_mcqs_falls_back_on_invalid_output():
    from pipeline.mcq_schema import generate_llm_mcqs
    items = [{"event_id": "good", "headline_en": "x"}, {"event_id": "bad", "headline_en": "y"}]
    replies = {"good": json.dumps(_llm_json(), ensure_ascii=False), "bad": "not json"}
    calls = []

    def route(prompt, **kw):
        calls.append(kw)
        return replies["good" if "NEWS (headline): x" in prompt else "bad"]

    out = generate_llm_mcqs(items, lambda it: SRC, route=route)
    assert set(out) == {"good"}
    assert all(c["task"] == "mcq" for c in calls)


def test_generate_mcqs_uses_llm_mcq_for_its_item_only():
    from pipeline.content import generate_mcqs
    llm = {"event_id": "e1", "question_en": "llm question for item one", "options": list("ABCDE")}
    out = generate_mcqs([{"event_id": "e1", "headline_en": "Item one headline here"}], llm_mcqs={"e1": llm})
    assert out == [llm]


def test_validate_mcqs_applies_schema_checks():
    from pipeline.content import validate_mcqs
    from pipeline.mcq_schema import normalize_item_mcq
    m = normalize_item_mcq(_llm_json(), {"event_id": "e1"})
    m["explanation_en"] = "NABARD is the implementing agency. " + m["explanation_en"]
    item = {"event_id": "e1", "headline_en": "Cabinet approves PACS scheme", "raw_facts": SRC,
            "key_points_en": [SRC], "detailed_explanation_en": SRC}
    valid, rejected = validate_mcqs([m], [item])
    assert valid or all("schema" not in e for r in rejected for e in r["errors"]), rejected
    bad = dict(m, options_hi=["", "", "", "", ""])
    _, rejected = validate_mcqs([bad], [item])
    assert any("Hindi text missing" in e for e in rejected[0]["errors"])


# --- Steps 4 / 7: no caps, no prefix, bilingual options, no padding -------
def test_explanation_and_static_gk_are_not_capped():
    from src.generate_pdf import _extract_explanation_points, _extract_static_gk_pairs
    from pipeline.mcq_schema import normalize_item_mcq
    m = normalize_item_mcq(_llm_json(explanation=[{"en": f"Distinct fact number {i} about cooperative credit {i*7}.", "hi": f"तथ्य {i}।"} for i in range(5)]), {"event_id": "e1"})
    assert len(_extract_explanation_points({}, m)) == 5
    assert len(_extract_static_gk_pairs({}, m)) == 4
    assert _extract_static_gk_pairs({}, m)[1] == ("Established – 12 July 1982", "स्थापना – 12 जुलाई 1982")


def test_options_are_bilingual_and_never_padded():
    from src.generate_pdf import _bilingual_options
    opts = _bilingual_options({"options": ["A1", "B1", "C1", "D1"], "options_hi": ["क", "ख", "ग", "घ"]})
    assert opts == [("A1", "क"), ("B1", "ख"), ("C1", "ग"), ("D1", "घ")]
    assert _bilingual_options({"options": ["X / एक", "None of the above"]}) == [("X", "एक")]


# --- Steps 6 / 8 / 9: rendering --------------------------------------------
def _qa():
    spec = importlib.util.spec_from_file_location("alp_pdf_qa_t410", str(REPO_ROOT / "agents" / "19_pdf_qa.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    from src.generate_pdf import generate_pdf
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    content = build_sample_content()
    out = tmp_path_factory.mktemp("t410") / "s.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(out))
    import fitz
    with fitz.open(str(out)) as doc:
        text = "\n".join(p.get_text() for p in doc)
    return out, content, text


def test_reference_layout_elements_present(sample):
    _, _, text = sample
    assert "Explanation | व्याख्या:" in text
    assert "Static GK (स्थैतिक सामान्य ज्ञान):" in text
    assert "Recent News Headlines Related to" in text
    assert "IMPORTANT ONE - LINER Current Affairs" in text
    assert "महत्वपूर्ण वन-लाइनर करंट अफेयर्स" in text
    assert "₹1,250 crore / ₹1,250 करोड़" in text           # bilingual option line
    assert "मुख्य बिंदु:" not in text                        # step 4 prefix removed
    assert "None of the above" not in text
    assert "20+" not in text
    assert "INDEX & TODAY" not in text and "ANSWER KEY" not in text  # optional, off by default


def test_qa_has_no_unshaped_devanagari(sample):
    path, content, _ = sample
    report = _qa().run_qa(Path(path), selected_items=content["items"], item_count=len(content["items"]))
    codes = {i.code for i in report.issues}
    assert "unshaped_devanagari" not in codes and "broken_devanagari_matras" not in codes
    assert report.passed


def test_body_starts_below_header_band(sample):
    import fitz
    path, _, _ = sample
    with fitz.open(str(path)) as doc:
        for page in list(doc)[1:]:
            for b in page.get_text("blocks"):
                if b[4].startswith("AGRI LEARNING POINT  |") or "UPSSSC AGTA" in b[4]:
                    continue
                assert b[1] >= 50, (page.number + 1, b[4][:40], b[1])


def test_one_liner_never_prints_private_static_gk_list():
    from pipeline.content import _build_category_one_liners
    ol = _build_category_one_liners([{"headline_en": "ISRO launches NVS satellite", "headline_hi": "इसरो ने उपग्रह लॉन्च किया",
                                      "static_facts": {"_static_gk_pairs": [("a", "b")]}}])
    assert "[(" not in ol[0]["text_en"] and "Key:" not in ol[0]["text_en"]


# --- Translator numeric validation -----------------------------------------
def test_translator_accepts_translated_units_but_not_wrong_numbers():
    from pipeline.ai_translator import _validate
    assert _validate("Repo rate kept at 6.50 per cent", "रेपो दर 6.50 प्रतिशत पर बनी रही")[0]
    assert _validate("₹1,250 crore scheme", "₹1250 करोड़ की योजना")[0]
    assert not _validate("Repo rate kept at 6.50 per cent", "रेपो दर 6.25 प्रतिशत पर बनी रही")[0]


# --- Step 10: orchestrator defaults come from the router --------------------
def test_orchestrator_defaults_follow_router(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "diagnostic-not-a-credential")
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    spec = importlib.util.spec_from_file_location("alp_orch_t410", str(REPO_ROOT / "agents" / "00_model_orchestrator.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    groq = [p for p in mod.provider_defaults() if p["name"] == "groq"][0]
    assert groq["model"] == "openai/gpt-oss-120b"
    assert not hasattr(mod, "PROVIDERS")

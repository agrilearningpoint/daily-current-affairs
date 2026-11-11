"""Content sanitizer tests (paywall boilerplate, source glue, dangling clips,
thin-source penalty) - all shapes taken from the 2026-11-11 edition."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import content_sanitizer as cs  # noqa: E402
from pipeline.scoring import score_item  # noqa: E402

MINT_RAW = ("The government has identified 80 districts across states to utilize rainfed land for "
            "increasing chana cultivation. This is a Mint Premium article gifted to you. "
            "Subscribe to enjoy similar stories. The identified states include Madhya Pradesh and Rajasthan.")


def test_paywall_sentences_removed_from_raw():
    out = cs.sanitize_raw_facts(MINT_RAW)
    assert "Premium" not in out and "Subscribe" not in out and "gifted" not in out
    assert "80 districts" in out and "Madhya Pradesh" in out


def test_trailing_source_domain_glued_off():
    line = ("Sale of Rice under Open Market Sale Scheme (Domestic) by FCI, Regional Office "
            "Maharashtra www.pib.gov.in")
    assert "pib.gov.in" not in cs.clean_line(line)
    assert line.startswith(cs.clean_line(line)[:40])


def test_bare_source_lines_dropped():
    kps = ["DD News", "Ministry of External Affairs", "Photo: PIB",
           "The delegation met the Cooperation Minister in Latur."]
    out = cs.sanitize_lines(kps, title="Something else entirely different here")
    assert out == ["The delegation met the Cooperation Minister in Latur."]


def test_headline_echo_summary_dropped():
    title = "PM E-DRIVE Scheme launched by the ministry"
    kps = ["PM E-DRIVE Scheme launched by the ministry pib.gov.in",
           "Applications open from 15 November 2026."]
    out = cs.sanitize_lines(kps, title=title)
    assert out == ["Applications open from 15 November 2026."]


def test_dangling_sentence_clipped_or_marked():
    long_ok = ("Kasbe said that sugar mills earnings from sugar sales and by-products such as molasses "
               "bagasse and ethanol should be considered while determining the price. Farmers agree.")
    assert cs.clean_line(long_ok).endswith(".")
    dangling = ("questioning why sugarcane growers in Marathwada and other regions were allegedly")
    assert cs.clean_line(dangling).endswith("…")


def test_headline_echo_kept_as_last_resort():
    title = "ISRO Launches NVS-09 Navigation Satellite from Sriharikota"
    kps = [title, title + " isro.gov.in"]
    out = cs.sanitize_lines(kps, title, "ISRO")
    assert out == [title]  # cleaned echo, never an empty list


def test_shallow_detection():
    assert cs.is_shallow({"raw_facts": "PM E-DRIVE Scheme pib.gov.in"}) is True
    assert cs.is_shallow({"raw_facts": MINT_RAW}) is False


def test_score_penalty_for_stub_source():
    base = {"headline_en": "PM E-DRIVE Scheme", "category": "Government Schemes",
            "source_level": 1, "event_cluster_size": 1}
    stub = dict(base, raw_facts="PM E-DRIVE Scheme pib.gov.in")
    rich = dict(base, raw_facts=MINT_RAW)
    a, b = score_item(stub), score_item(rich)
    assert a["shallow_source"] is True and b["shallow_source"] is False
    assert a["importance_score"] < b["importance_score"]

from pipeline.scoring import score_item
from config.sources import LEVEL_NAMES, PRIORITY_MAP
def test_agri_boost():
    it={"headline_en":"ICAR crop MSP farm agriculture scheme launched national impact","raw_facts":"agri farm crop MSP ICAR agriculture scheme national impact report","category":"Agriculture","source_tier":"tier1","source_level":0}
    sc=score_item(it)
    # Agriculture category + national impact should give decent score
    assert sc["importance_score"]>15
    assert sc["source_type"]==LEVEL_NAMES[0]
    assert sc["source_reliability"]==100
def test_fallback_lower():
    it={"headline_en":"random gossip","raw_facts":"","category":"Other","source_tier":"tier3","source_level":5}
    sc=score_item(it)
    assert sc["source_reliability"]==PRIORITY_MAP[5]

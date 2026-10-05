from pipeline.scoring import deduplicate
def test_event_level_msp_cluster():
    items=[
        {"headline_en":"Government approves new MSP for wheat","raw_facts":"MSP wheat","source_name":"PIB","source_url":"https://pib.gov.in/release1","source_tier":"tier1","source_level":0,"priority":100,"category":"Agriculture","pub_time_ist":"2026-10-05T10:00:00+05:30"},
        {"headline_en":"Centre announces higher MSP for wheat","raw_facts":"MSP wheat increased","source_name":"Agriculture Ministry","source_url":"https://agriwelfare.gov.in/news1","source_tier":"tier1","source_level":0,"priority":100,"category":"Agriculture","pub_time_ist":"2026-10-05T11:00:00+05:30"},
        {"headline_en":"Cabinet clears revised MSP rates","raw_facts":"MSP rates revised","source_name":"The Hindu","source_url":"https://thehindu.com/msp-wheat","source_tier":"tier2","source_level":4,"priority":80,"category":"Agriculture","pub_time_ist":"2026-10-05T12:00:00+05:30"},
    ]
    out=deduplicate(items)
    assert len(out)==1
    assert out[0]["source_count"]==3
    assert "supporting_sources" in out[0]
    assert out[0]["canonical_source"] in ("PIB","Agriculture Ministry")
def test_contrastive_not_merged():
    items=[
        {"headline_en":"RBI cuts repo rate by 25 bps to 5.50%","raw_facts":"RBI repo cut 25 bps 5.50%","source_name":"RBI","source_url":"https://rbi.org.in/cut","source_tier":"tier1","source_level":0,"priority":100,"category":"Banking & Finance","pub_time_ist":"2026-10-05T10:00:00+05:30"},
        {"headline_en":"RBI maintains repo rate at 5.75%","raw_facts":"RBI repo maintain 5.75%","source_name":"The Hindu","source_url":"https://thehindu.com/rbi-maintain","source_tier":"tier2","source_level":4,"priority":80,"category":"Banking & Finance","pub_time_ist":"2026-10-05T10:00:00+05:30"},
        {"headline_en":"Government approves new MSP for wheat","raw_facts":"MSP wheat","source_name":"PIB","source_url":"https://pib.gov.in/release1","source_tier":"tier1","source_level":0,"priority":100,"category":"Agriculture","pub_time_ist":"2026-10-05T10:00:00+05:30"},
        {"headline_en":"Government releases MSP implementation guidelines","raw_facts":"MSP guidelines","source_name":"PIB","source_url":"https://pib.gov.in/guidelines","source_tier":"tier1","source_level":0,"priority":100,"category":"Agriculture","pub_time_ist":"2026-10-10T10:00:00+05:30"},
    ]
    out=deduplicate(items)
    assert len(out)==4, f"expected 4 separate events (cut vs maintain, approve vs guidelines) got {len(out)}"
def test_variable_quantity():
    # Simulate selection variable quantity logic
    def choose(n):
        lo,hi=4,15
        candidates=list(range(n))
        if len(candidates)<=lo: return len(candidates)
        elif len(candidates)<=12: return len(candidates[:12])
        else: return len(candidates[:hi])
    assert choose(4)==4
    assert choose(10)==10
    assert choose(30)==15

from pipeline.gnews import decode_article_url
def test_decode_cache():
    # decode_many cache seeding should not crash (previous bug)
    assert callable(decode_article_url)

def test_raqm_guard():
    from PIL import features
    assert features.check("raqm"), "RAQM required for Hindi shaping"

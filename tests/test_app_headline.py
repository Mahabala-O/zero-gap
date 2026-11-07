from streamlit.testing.v1 import AppTest


def test_headline_flags_separate_draws():
    # Default view is Tustin (paired) vs Santa Ana (separate draws, n_paired=6).
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "drawn separately" in text and "Santa Ana" in text.split("ASSUMPTION: too few")[1]
    assert "Tustin" not in text.split("ASSUMPTION: too few")[1]


def test_headline_flags_same_day_city():
    # Anaheim reports ~72% same-day entitlement -> permit rows; Tustin ~2%.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[1].select_index(at.selectbox[1].options.index("Anaheim")).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Caution: most of Anaheim's" in text
    assert "Tustin's" not in text
    at.selectbox[1].select_index(at.selectbox[1].options.index("Santa Ana")).run()
    assert "Caution: most of" not in " ".join(m.value for m in at.markdown)

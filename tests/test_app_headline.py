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


def test_headline_same_day_two_cities_plural():
    # Anaheim (~72%) and Fullerton (~85%) are both above the same-day threshold.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[0].select_index(at.selectbox[0].options.index("Anaheim")).run()
    at.selectbox[1].select_index(at.selectbox[1].options.index("Fullerton")).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    caution = text.split("Caution: most of")[1]
    assert "Anaheim and Fullerton's each" in caution
    assert "their speed there" in caution and "its speed" not in caution


def test_tab_b_best_quartile_shows_n():
    # UX rubric #4: every benchmark shows its n. The OC best quartile cell names its city count,
    # and that count matches peer_medians (n >= MIN_N, same-day cities left out).
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    tables = [d.value for d in at.dataframe if "OC best quartile (n)" in d.value.columns]
    assert len(tables) == 1
    cells = list(tables[0]["OC best quartile (n)"])
    assert all(c == "unknown" or c.endswith(" cities)") for c in cells)
    import analysis as A
    df = A.add_durations(A.load_a2())
    for cell, stage in zip(cells, ["ent_to_permit", "permit_to_co"]):
        peers = A.peer_medians(df, None, stage)
        assert f"({int((~peers['same_day']).sum())} cities)" in cell


def test_tab_b_explains_co():
    # UX rubric #5: Tab B's stage table says "Permit → CO"; CO is spelled out next to it.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    caps = [c.value for c in at.caption if "Best quartile" in c.value]
    assert len(caps) == 1 and "CO = certificate of occupancy" in caps[0]

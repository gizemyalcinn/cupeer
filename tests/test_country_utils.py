from src.scraping.country_utils import resolve_location


def test_recognizes_turkish_country_name():
    code, _, is_country = resolve_location("Türkiye")
    assert code == "tr"
    assert is_country is True


def test_recognizes_english_country_name_case_insensitive():
    code, text, is_country = resolve_location("united states")
    assert code == "us"
    assert text == "United States"
    assert is_country is True


def test_city_name_falls_back_to_turkey_without_rewriting_text():
    code, text, is_country = resolve_location("Kocaeli")
    assert code == "tr"
    assert text == "Kocaeli"
    assert is_country is False


def test_empty_location_defaults_to_turkey():
    code, _, is_country = resolve_location("")
    assert code == "tr"
    assert is_country is False

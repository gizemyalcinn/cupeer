"""Konum metninden ülke algılama — Indeed'in ülke koduna, ya da diğer platformlar
için standart İngilizce ülke adına çevirir. Yalnızca TAM ülke adı eşleşmelerini
tanır (örn. "Ankara" gibi bir şehir adını ülke sanmaz)."""

_TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "İ": "i", "I": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
})


def _normalize(text: str) -> str:
    return text.strip().translate(_TR_MAP).lower()


_COUNTRY_ALIASES: dict[str, tuple[str, str]] = {
    "turkiye": ("tr", "Turkey"),
    "turkey": ("tr", "Turkey"),
    "abd": ("us", "United States"),
    "amerika": ("us", "United States"),
    "amerika birlesik devletleri": ("us", "United States"),
    "united states": ("us", "United States"),
    "usa": ("us", "United States"),
    "us": ("us", "United States"),
    "ingiltere": ("uk", "United Kingdom"),
    "birlesik krallik": ("uk", "United Kingdom"),
    "united kingdom": ("uk", "United Kingdom"),
    "uk": ("uk", "United Kingdom"),
    "almanya": ("de", "Germany"),
    "germany": ("de", "Germany"),
    "fransa": ("fr", "France"),
    "france": ("fr", "France"),
    "hollanda": ("nl", "Netherlands"),
    "netherlands": ("nl", "Netherlands"),
    "kanada": ("ca", "Canada"),
    "canada": ("ca", "Canada"),
    "avustralya": ("au", "Australia"),
    "australia": ("au", "Australia"),
    "ispanya": ("es", "Spain"),
    "spain": ("es", "Spain"),
    "italya": ("it", "Italy"),
    "italy": ("it", "Italy"),
    "irlanda": ("ie", "Ireland"),
    "ireland": ("ie", "Ireland"),
    "isvicre": ("ch", "Switzerland"),
    "switzerland": ("ch", "Switzerland"),
    "polonya": ("pl", "Poland"),
    "poland": ("pl", "Poland"),
    "birlesik arap emirlikleri": ("ae", "United Arab Emirates"),
    "bae": ("ae", "United Arab Emirates"),
    "uae": ("ae", "United Arab Emirates"),
    "united arab emirates": ("ae", "United Arab Emirates"),
}


def resolve_location(location: str) -> tuple[str, str, bool]:
    """
    Konum metnini yorumlar.

    Döner: (indeed_ulke_kodu, actorlere_gonderilecek_metin, ulke_seviyesinde_mi)

    - Metin tanınan bir ülke adıysa: o ülkenin Indeed kodu + standart İngilizce
      adı döner, üçüncü değer True olur (şehir filtresi yok, ülke geneli arama).
    - Aksi halde (boş ya da bir şehir adı): varsayılan "tr" kodu + yazılan metin
      aynen döner, üçüncü değer False olur.
    """
    match = _COUNTRY_ALIASES.get(_normalize(location))
    if match:
        code, english_name = match
        return code, english_name, True
    return "tr", location.strip(), False


_ALL_COUNTRY_NAMES: list[tuple[str, str]] = sorted(set(_COUNTRY_ALIASES.values()))


def location_matches_country(job_location: str | None, country_code: str, country_name: str) -> bool:
    """Bir ilanın 'location' metninin, aranan ülkeyle uyumlu olup olmadığını kontrol eder."""
    if not job_location:
        return True  # konum bilgisi yoksa, dışlamak yerine göstermeyi tercih ediyoruz

    text = job_location.lower()

    if country_code == "tr":
        # Türkiye aranıyorsa: metinde başka bilinen bir ülke adı geçmediği sürece kabul et
        for code, name in _ALL_COUNTRY_NAMES:
            if code != "tr" and name.lower() in text:
                return False
        return True

    return country_name.lower() in text or "remote" in text

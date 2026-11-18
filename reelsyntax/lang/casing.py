import unicodedata

TURKISH_LOCALES = frozenset({"tr", "az"})
GERMAN_LOCALES = frozenset({"de"})


def primary_subtag(locale: str) -> str:
    if not locale:
        return "en"
    return locale.strip().replace("_", "-").split("-", 1)[0].lower()


def locale_upper(text: str, locale: str = "en") -> str:
    normalized = unicodedata.normalize("NFC", text)
    lang = primary_subtag(locale)
    if lang in TURKISH_LOCALES:
        step = normalized.replace("i", "İ").replace("ı", "I")
        return step.upper()
    if lang in GERMAN_LOCALES:
        step = normalized.replace("ß", "SS").replace("ẞ", "SS")
        return step.upper()
    return normalized.upper()


def locale_lower(text: str, locale: str = "en") -> str:
    normalized = unicodedata.normalize("NFC", text)
    lang = primary_subtag(locale)
    if lang in TURKISH_LOCALES:
        cleaned = normalized.replace("I\u0307", "i").replace("İ", "i").replace("I", "ı")
        return cleaned.lower()
    if lang in GERMAN_LOCALES:
        return normalized.replace("ẞ", "ß").lower()
    return normalized.lower()


def locale_title(text: str, locale: str = "en") -> str:
    words = text.split(" ")
    transformed: list[str] = []
    for word in words:
        if not word:
            transformed.append(word)
            continue
        first = locale_upper(word[:1], locale)
        rest = locale_lower(word[1:], locale)
        transformed.append(first + rest)
    return " ".join(transformed)

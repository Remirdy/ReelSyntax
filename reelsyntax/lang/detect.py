import re
import unicodedata

TR_CHARS = frozenset("çğıöşüÇĞİÖŞÜ")
TR_UNIQUE_CHARS = frozenset("ğışĞİŞ")
DE_CHARS = frozenset("äöüßÄÖÜẞ")
DE_UNIQUE_CHARS = frozenset("ßẞ")
ES_UNIQUE_CHARS = frozenset("ñÑ¿¡")
FR_UNIQUE_CHARS = frozenset("èùîïœæÈÙÎÏŒÆ")
PT_UNIQUE_CHARS = frozenset("ãõÃÕ")

STOPWORDS_BY_LANG: dict[str, frozenset[str]] = {
    "tr": frozenset({
        "bir", "ve", "ile", "için", "icin", "değil", "degil", "olmasın", "olmasin",
        "yazısız", "yazisiz", "kamera", "sabit", "sahne", "müzik", "muzik", "seslendirme",
        "altyazı", "altyazi", "lütfen", "lutfen", "gibi", "olarak", "dikey", "yatay",
        "kısa", "kisa", "ipucu", "renk", "hareketli",
    }),
    "de": frozenset({
        "und", "mit", "ohne", "für", "fuer", "nicht", "bitte", "eine", "einen", "einem",
        "der", "die", "das", "den", "dem", "des", "kein", "keine", "feste", "schwarzbilder",
        "bildfrequenz", "untertitel", "musik", "sprache", "kurzvideo", "ruhigen", "farben",
    }),
    "en": frozenset({
        "the", "and", "with", "without", "for", "from", "make", "create", "scene", "camera",
        "locked", "captions", "subtitles", "music", "voiceover", "calm", "colors", "tips",
        "short", "vertical", "please", "keep",
    }),
    "es": frozenset({
        "con", "sin", "para", "una", "por", "del", "las", "los", "cámara", "camara",
        "fija", "texto", "música", "musica", "fotogramas", "consejos", "colores",
        "tranquilos", "subtítulos", "subtitulos", "corto", "escena", "ritmo", "vídeo",
    }),
    "fr": frozenset({
        "avec", "sans", "pour", "une", "des", "les", "dans", "caméra", "camera",
        "fixe", "texte", "musique", "images", "cadence", "vidéo", "couleurs",
        "calmes", "conseils", "courte", "court", "scène", "rythme", "sous-titres",
    }),
    "pt": frozenset({
        "com", "sem", "para", "uma", "dos", "das", "câmera", "camera",
        "fixa", "texto", "música", "musica", "quadros", "vídeo", "cores",
        "calmas", "dicas", "curto", "cena", "ritmo", "legendas", "passos",
    }),
}

TR_SUFFIX_RE = re.compile(r"(?:ları|leri|ların|lerin|sız|siz|suz|süz|lığı|liği|luğu|lüğü|dan|den|tan|ten)\b")
DE_SUFFIX_RE = re.compile(r"(?:ung|ungen|keit|keiten|schaft|schaften|isch|ische|ischen)\b")
ES_SUFFIX_RE = re.compile(r"(?:ción|ciones|miento|mientos|dad|dades)\b")
FR_SUFFIX_RE = re.compile(r"(?:tion|tions|ement|ements|ment)\b")
PT_SUFFIX_RE = re.compile(r"(?:ção|ções|mento|mentos|dade|dades)\b")


def normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def fold_accents_for_match(text: str) -> str:
    lowered = unicodedata.normalize("NFC", text).replace("İ", "i").replace("ı", "i").replace("ß", "ss").replace("ẞ", "ss").casefold()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def detect_script(text: str) -> str:
    counts = {"Arab": 0, "Hebr": 0, "Hani": 0, "Jpan": 0, "Hang": 0, "Cyrl": 0, "Latn": 0}
    for ch in text:
        code = ord(ch)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0xFB50 <= code <= 0xFDFF or 0xFE70 <= code <= 0xFEFF:
            counts["Arab"] += 1
        elif 0x0590 <= code <= 0x05FF:
            counts["Hebr"] += 1
        elif 0x3040 <= code <= 0x30FF:
            counts["Jpan"] += 1
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            counts["Hang"] += 1
        elif 0x4E00 <= code <= 0x9FFF:
            counts["Hani"] += 1
        elif 0x0400 <= code <= 0x04FF:
            counts["Cyrl"] += 1
        elif ch.isalpha():
            counts["Latn"] += 1
    if counts["Jpan"] > 0:
        return "Jpan"
    best_script, best_count = max(counts.items(), key=lambda item: item[1])
    return best_script if best_count > 0 else "Latn"


def detect_language(text: str, default: str = "en") -> str:
    cleaned = normalize_nfc(text).strip()
    if not cleaned:
        return default
    script = detect_script(cleaned)
    if script == "Arab":
        return "ar"
    if script == "Hebr":
        return "he"
    if script == "Jpan":
        return "ja"
    if script == "Hang":
        return "ko"
    if script == "Hani":
        return "zh"

    scores: dict[str, float] = {lang: 0.0 for lang in STOPWORDS_BY_LANG}
    for ch in cleaned:
        if ch in TR_UNIQUE_CHARS:
            scores["tr"] += 3.5
        elif ch in TR_CHARS:
            scores["tr"] += 1.2
        if ch in DE_UNIQUE_CHARS:
            scores["de"] += 4.0
        elif ch in DE_CHARS:
            scores["de"] += 1.4
        if ch in ES_UNIQUE_CHARS:
            scores["es"] += 3.5
        if ch in FR_UNIQUE_CHARS:
            scores["fr"] += 3.0
        elif ch in "éêàÉÊÀ":
            scores["fr"] += 0.6
        if ch in PT_UNIQUE_CHARS:
            scores["pt"] += 3.5
        if ch in "çÇ":
            scores["fr"] += 0.4
            scores["pt"] += 0.4

    tokens = re.findall(r"[^\W\d_]+", cleaned.lower(), flags=re.UNICODE)
    for tok in tokens:
        for lang, words in STOPWORDS_BY_LANG.items():
            if tok in words:
                scores[lang] += 2.5
        if TR_SUFFIX_RE.search(tok) and len(tok) >= 6:
            scores["tr"] += 1.5
        if DE_SUFFIX_RE.search(tok) and len(tok) >= 6:
            scores["de"] += 1.5
        if ES_SUFFIX_RE.search(tok) and len(tok) >= 6:
            scores["es"] += 1.2
        if FR_SUFFIX_RE.search(tok) and len(tok) >= 6:
            scores["fr"] += 1.2
        if PT_SUFFIX_RE.search(tok) and len(tok) >= 6:
            scores["pt"] += 1.2

    best_lang, best_score = max(scores.items(), key=lambda item: (item[1], item[0] == default))
    if best_score < 1.5:
        return default
    return best_lang

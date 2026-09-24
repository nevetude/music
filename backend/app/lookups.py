"""Genius отдаёт только двухбуквенный код языка (song.language / album.language),
страны там нет вообще. Показываем и язык, и страну — страну выводим
приблизительно, по языку (это упрощение, не географическая точность)."""

# код -> (название языка, "типичная" страна для показа)
LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "United States"),
    "es": ("Spanish", "Spain"),
    "fr": ("French", "France"),
    "de": ("German", "Germany"),
    "pt": ("Portuguese", "Brazil"),
    "it": ("Italian", "Italy"),
    "ru": ("Russian", "Russia"),
    "ja": ("Japanese", "Japan"),
    "ko": ("Korean", "South Korea"),
    "zh": ("Chinese", "China"),
}


def language_name(code: str | None) -> str | None:
    if not code:
        return None
    entry = LANGUAGES.get(code.lower())
    return entry[0] if entry else code


def country_name(code: str | None) -> str | None:
    if not code:
        return None
    entry = LANGUAGES.get(code.lower())
    return entry[1] if entry else None

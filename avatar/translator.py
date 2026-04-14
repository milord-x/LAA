"""
Offline translator for sign language lookup.
Translates RU/KZ text to EN so we can match the full 374-sign EN dictionary.
Uses argostranslate (offline, no API key needed).
"""

import threading
from typing import Optional

_lock = threading.Lock()
_loaded: dict[str, object] = {}  # lang_pair -> translate function


def _load_pair(src: str, tgt: str = "en") -> Optional[object]:
    """Load argostranslate package for src->tgt. Downloads if not cached."""
    key = f"{src}-{tgt}"
    if key in _loaded:
        return _loaded[key]
    try:
        from argostranslate import package, translate
        package.update_package_index()
        available = package.get_available_packages()
        pkg = next(
            (p for p in available if p.from_code == src and p.to_code == tgt),
            None,
        )
        if pkg is None:
            print(f"[Translator] No package found for {src}->{tgt}")
            return None
        if not pkg.is_installed():
            print(f"[Translator] Downloading {src}->{tgt} package (~50MB)...")
            package.install_from_path(pkg.download())
            print(f"[Translator] {src}->{tgt} installed.")
        installed = translate.get_installed_languages()
        src_lang = next((l for l in installed if l.code == src), None)
        if src_lang is None:
            return None
        translation = src_lang.get_translation(
            next(l for l in installed if l.code == tgt)
        )
        _loaded[key] = translation
        return translation
    except Exception as e:
        print(f"[Translator] Failed to load {src}->{tgt}: {e}")
        return None


def _detect_lang(text: str) -> str:
    """Simple heuristic: Kazakh has specific chars, else assume RU."""
    kaz_chars = set("әіңғүұқөһ")
    if any(c in kaz_chars for c in text.lower()):
        return "kz"
    # Check for Cyrillic — assume RU
    if any("\u0400" <= c <= "\u04ff" for c in text):
        return "ru"
    return "en"


def translate_to_en(text: str) -> str:
    """
    Translate text to English for sign lookup.
    Returns original text if translation unavailable or already EN.
    """
    lang = _detect_lang(text)
    if lang == "en":
        return text

    # argostranslate uses "kz" but package may be under different code
    src = "ru" if lang == "kz" else lang

    with _lock:
        translator = _load_pair(src, "en")

    if translator is None:
        return text

    try:
        result = translator.translate(text)
        return result
    except Exception as e:
        print(f"[Translator] translate failed: {e}")
        return text


def preload_async():
    """Preload RU->EN in background so first segment isn't slow."""
    t = threading.Thread(target=lambda: _load_pair("ru", "en"), daemon=True)
    t.start()

"""
Offline translator for sign language lookup.
Translates RU/KZ text to EN so we can match the full 374-sign EN dictionary.
Uses argostranslate (offline, no API key needed).
"""

import threading
from typing import Optional

_lock = threading.Lock()
_loaded: dict[str, object] = {}


def _load_pair(src: str, tgt: str = "en") -> Optional[object]:
    key = f"{src}-{tgt}"
    if key in _loaded:
        return _loaded[key]
    try:
        from argostranslate import translate

        langs = translate.get_installed_languages()
        src_lang = next((l for l in langs if l.code == src), None)
        tgt_lang = next((l for l in langs if l.code == tgt), None)

        if src_lang is None or tgt_lang is None:
            from argostranslate import package
            package.update_package_index()
            available = package.get_available_packages()
            pkg = next(
                (p for p in available if p.from_code == src and p.to_code == tgt),
                None,
            )
            if pkg is None:
                print(f"[Translator] No package for {src}->{tgt}")
                return None
            print(f"[Translator] Downloading {src}->{tgt}...")
            pkg.install()
            langs = translate.get_installed_languages()
            src_lang = next((l for l in langs if l.code == src), None)
            tgt_lang = next((l for l in langs if l.code == tgt), None)

        if src_lang is None or tgt_lang is None:
            return None

        translation = src_lang.get_translation(tgt_lang)
        _loaded[key] = translation
        return translation
    except Exception as e:
        print(f"[Translator] Failed {src}->{tgt}: {e}")
        return None


def _detect_lang(text: str) -> str:
    kaz_chars = set("әіңғүұқөһ")
    if any(c in kaz_chars for c in text.lower()):
        return "kz"
    if any("\u0400" <= c <= "\u04ff" for c in text):
        return "ru"
    return "en"


def translate_to_en(text: str) -> str:
    lang = _detect_lang(text)
    if lang == "en":
        return text
    src = "ru"  # argostranslate uses ru for both ru and kz fallback
    with _lock:
        translator = _load_pair(src, "en")
    if translator is None:
        return text
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"[Translator] translate error: {e}")
        return text


def preload_async():
    t = threading.Thread(target=lambda: _load_pair("ru", "en"), daemon=True)
    t.start()

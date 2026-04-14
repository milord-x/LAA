"""
SiGML lookup: maps keywords to SiGML sign fragments.
Pool of 35+ validated signs for CWASA avatar variety.
"""

import hashlib

_SIGN_MAP: dict[str, str] = {
    # ── Core signs (validated) ────────────────────────────────────────────────
    "hello":      '<hns_sign gloss="hello"><hamnosys_nonmanual><hnm_mouthpicture picture="hVlU"/></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hambetween/><hamfinger2345/><hamextfingeru/><hampalmd/><hamshouldertop/><hamlrat/><hamarmextended/><hamswinging/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "good":       '<hns_sign gloss="good"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchopen/><hamextfingeru/><hampalml/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "yes":        '<hns_sign gloss="yes"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingero/><hampalmd/><hamstomach/><hamlrat/><hamclose/><hamnodding/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "no":         '<hns_sign gloss="no"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinch12/><hamfingerstraightmod/><hamindexfinger/><hammiddlefinger/><hamextfingerul/><hampalmd/><hamshoulders/><hamlrat/></hamnosys_manual></hns_sign>',
    "please":     '<hns_sign gloss="please"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchall/><hamextfingero/><hampalmu/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "understand": '<hns_sign gloss="understand"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrat/><hamclose/><hamreplace/><hamfinger2/><hamthumboutmod/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "know":       '<hns_sign gloss="know"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamfingerstraightmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrbeside/><hamseqbegin/><hammoveor/><hammoveil/><hamseqend/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    "not":        '<hns_sign gloss="not"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamcee12/><hamindexfinger/><hammiddlefinger/><hamextfingeru/><hampalmdl/><hamshoulders/><hamclose/><hamreplace/><hampinch12/><hamindexfinger/><hammiddlefinger/><hamextfingeru/><hampalmdl/><hamshoulders/><hamclose/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "now":        '<hns_sign gloss="now"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamextfingerdl/><hampalmul/><hambetween/><hampalmr/><hamchest/><hammoved/><hamlargemod/></hamnosys_manual></hns_sign>',
    "name":       '<hns_sign gloss="name"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger23/><hamthumbacrossmod/><hamextfingerl/><hambetween/><hamextfingerul/><hampalmd/><hamforehead/><hamparbegin/><hammoveo/><hamreplace/><hamextfingero/><hampalmd/><hamparend/></hamnosys_manual></hns_sign>',
    "help":       '<hns_sign gloss="help"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmpar/><hamparbegin/><hamfist/><hamthumboutmod/><hamplus/><hamflathand/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingerl/><hampalml/><hamplus/><hamextfingeror/><hampalmu/><hamparend/><hamparbegin/><hampalm/><hamplus/><hampinkyside/><hamparend/><hamtouch/><hammovei/></hamnosys_manual></hns_sign>',
    "announce":   '<hns_sign gloss="announce"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmpar/><hampinchall/><hamextfingeru/><hampalml/><hamparbegin/><hamfingertip/><hamthumb/><hamindexfinger/><hamplus/><hamfingertip/><hamthumb/><hamindexfinger/><hamparend/><hamtouch/><hamchin/><hamparbegin/><hamreplace/><hamfinger2345/><hamextfingeruo/><hampalmd/><hamclose/><hamshoulders/><hamparend/></hamnosys_manual></hns_sign>',
    # ── Actions ───────────────────────────────────────────────────────────────
    "come":    '<hns_sign gloss="come"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamextfingerul/><hambetween/><hamextfingeru/><hampalmdr/><hamlrat/><hamshouldertop/><hamparbegin/><hammoveir/><hamreplace/><hamflathand/><hamfingerbendmod/><hamreplace/><hamflathand/><hamfingerhookmod/><hamextfingerul/><hambetween/><hamextfingero/><hampalmd/><hamparend/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "go":      '<hns_sign gloss="go"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hamextfingerol/><hampalml/><hamshoulders/><hamclose/><hamparbegin/><hammover/><hamlargemod/><hamarcd/><hamlargemod/><hamreplace/><hamflathand/><hamextfingeru/><hampalmd/><hamparend/></hamnosys_manual></hns_sign>',
    "eat":     '<hns_sign gloss="eat"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamextfingeru/><hampalmu/><hamteeth/><hamclose/><hamnomotion/><hammoved/><hamchest/></hamnosys_manual></hns_sign>',
    "drink":   '<hns_sign gloss="drink"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingeru/><hampalmd/><hambetween/><hampalml/><hamlips/><hamlrat/><hamclose/></hamnosys_manual></hns_sign>',
    "sleep":   '<hns_sign gloss="sleep"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamparbegin/><hamflathand/><hamplus/><hamflathand/><hamparend/><hamparbegin/><hamextfingerur/><hampalmu/><hamplus/><hamextfingerur/><hampalmd/><hamparend/><hamparbegin/><hamlrat/><hamneck/><hamclose/><hamplus/><hamlrat/><hamneck/><hamclose/><hamparend/><hamparbegin/><hampalm/><hamplus/><hampalm/><hamparend/><hamtouch/></hamnosys_manual></hns_sign>',
    "think":   '<hns_sign gloss="think"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger2/><hamthumbacrossmod/><hamextfingerul/><hampalmul/><hamear/><hamtouch/><hamnomotion/></hamnosys_manual></hns_sign>',
    "read":    '<hns_sign gloss="read"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamparbegin/><hamfinger23/><hamthumbacrossmod/><hamplus/><hamflathand/><hamparend/><hamparbegin/><hamextfingerol/><hampalmdl/><hamplus/><hamextfingeru/><hampalmu/><hamparend/><hamparbegin/><hamindexfinger/><hamfingertip/><hamplus/><hamindexfinger/><hamfingertip/><hamparend/><hamclose/><hamchest/><hammoved/><hamlargemod/><hamwavy/><hamsmallmod/></hamnosys_manual></hns_sign>',
    "learn":   '<hns_sign gloss="learn"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamparbegin/><hampinch12/><hamplus/><hamflathand/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingerl/><hamplus/><hamextfingerr/><hamparend/><hamparbegin/><hampalmd/><hamplus/><hampalmu/><hamparend/><hamparbegin/><hampalm/><hamplus/><hammiddlefinger/><hamfingermidjoint/><hamparend/><hamtouch/><hamchest/><hamclose/><hammoveu/><hamforehead/><hamlrat/><hamtouch/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "teach":   '<hns_sign gloss="teach"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hamextfingerl/><hampalmul/><hamchest/><hamclose/><hammoveo/><hamarcu/><hamsmallmod/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    "answer":  '<hns_sign gloss="answer"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamparbegin/><hamfist/><hamthumboutmod/><hamplus/><hamfist/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingeru/><hampalmd/><hambetween/><hampalml/><hamplus/><hamextfingeru/><hampalmd/><hambetween/><hampalmr/><hamparend/><hamparbegin/><hamthumb/><hamfingertip/><hamplus/><hamthumb/><hamfingertip/><hamparend/><hamtouch/><hamshoulders/><hammoveo/></hamnosys_manual></hns_sign>',
    "call":    '<hns_sign gloss="call"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamextfingerul/><hambetween/><hamextfingeru/><hampalmdr/><hamlrat/><hamshoulders/><hamreplace/><hamflathand/><hamfingerstraightmod/><hamextfingerul/><hambetween/><hamextfingeru/><hampalmdr/><hamlrat/><hamshoulders/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "send":    '<hns_sign gloss="send"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamparbegin/><hampinchall/><hamplus/><hamflathand/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingerol/><hampalmd/><hamplus/><hamextfingeror/><hampalmd/><hamparend/><hamparbegin/><hamstomach/><hamplus/><hamstomach/><hambetween/><hamchest/><hamparend/><hamparbegin/><hamreplace/><hamfinger2345/><hamthumboutmod/><hammoveo/><hamparend/></hamnosys_manual></hns_sign>',
    "open":    '<hns_sign gloss="open"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamextfingerl/><hampalml/><hamchest/><hamclose/><hamreplace/><hamextfingero/></hamnosys_manual></hns_sign>',
    "close":   '<hns_sign gloss="close"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamthumbopenmod/><hamextfingero/><hampalmd/><hamclose/><hammovel/><hamarcu/><hamtouch/></hamnosys_manual></hns_sign>',
    "finish":  '<hns_sign gloss="finish"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamthumboutmod/><hamextfingero/><hampalmu/><hamstomach/><hamlrat/><hamclose/><hamparbegin/><hamreplace/><hamfinger2345/><hamthumboutmod/><hampalmd/><hamparend/></hamnosys_manual></hns_sign>',
    # ── Time ─────────────────────────────────────────────────────────────────
    "morning": '<hns_sign gloss="morning"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchall/><hamextfingero/><hampalmu/><hamstomach/><hamlrat/><hamparbegin/><hammoveu/><hamreplace/><hamfinger2345/><hamthumboutmod/><hamextfingero/><hampalmu/><hamparend/><hamhead/><hamlrat/></hamnosys_manual></hns_sign>',
    "evening": '<hns_sign gloss="evening"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamcee12/><hammiddlefinger/><hamringfinger/><hampinky/><hamextfingero/><hampalmu/><hamheadtop/><hammoved/><hamlargemod/><hamstomach/></hamnosys_manual></hns_sign>',
    "day":     '<hns_sign gloss="day"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamparbegin/><hamfinger2/><hamplus/><hamflathand/><hamparend/><hamparbegin/><hamextfingeru/><hampalmu/><hamplus/><hamextfingerr/><hampalmd/><hamparend/><hamparbegin/><hamhead/><hamlrat/><hamplus/><hamstomach/><hamlrat/><hamtouch/><hamparend/><hamparbegin/><hammovedl/><hamlargemod/><hamreplace/><hamextfingerdl/><hampalmd/><hamparend/><hamlrat/><hamchest/></hamnosys_manual></hns_sign>',
    "night":   '<hns_sign gloss="night"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger2345/><hamthumboutmod/><hamfingerstraightmod/><hamextfingero/><hampalmu/><hamnose/><hamclose/><hamnomotion/><hamparbegin/><hammoved/><hamreplace/><hampinchall/><hamextfingero/><hampalmu/><hamparend/></hamnosys_manual></hns_sign>',
    # ── Emotions ─────────────────────────────────────────────────────────────
    "sad":   '<hns_sign gloss="sad"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger2345/><hamthumboutmod/><hamextfingerl/><hampalml/><hamshoulders/><hamtouch/><hamparbegin/><hammovedo/><hamlargemod/><hamreplace/><hamfinger2345/><hamthumbopenmod/><hamfingerbendmod/><hambetween/><hamceeall/><hamthumbacrossmod/><hamextfingerl/><hampalmu/><hamparend/></hamnosys_manual></hns_sign>',
    "love":  '<hns_sign gloss="love"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamextfingerl/><hampalml/><hamshoulders/><hamclose/><hamreplace/><hampinchall/><hammovei/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "like":  '<hns_sign gloss="like"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinch12/><hamthumboutmod/><hamextfingerul/><hampalml/><hamchest/><hammoveo/><hamlargemod/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "laugh": '<hns_sign gloss="laugh"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hampinch12/><hamthumboutmod/><hamextfingeru/><hampalmdr/><hamlrat/><hamlips/><hamparbegin/><hammoveu/><hamsmallmod/><hamreplace/><hammoved/><hamsmallmod/><hamparend/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    "cry":   '<hns_sign gloss="cry"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamfinger2/><hamthumbacrossmod/><hamextfingeru/><hampalml/><hamear/><hamlrat/><hamparbegin/><hammoved/><hamlargemod/><hamreplace/><hamindexfinger/><hamthumbacrossmod/><hamparend/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    # ── Descriptors ──────────────────────────────────────────────────────────
    "bad":       '<hns_sign gloss="bad"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hamextfingerol/><hampalmu/><hamchin/><hamlrat/><hamclose/><hamreplace/><hampinchall/></hamnosys_manual></hns_sign>',
    "big":       '<hns_sign gloss="big"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamthumboutmod/><hamextfingerol/><hampalml/><hamshoulders/><hammoveo/><hamlargemod/></hamnosys_manual></hns_sign>',
    "small":     '<hns_sign gloss="small"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamthumboutmod/><hamextfingerol/><hampalml/><hamshoulders/><hammovei/><hamlargemod/></hamnosys_manual></hns_sign>',
    "slow":      '<hns_sign gloss="slow"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hamextfingerdl/><hampalmu/><hamhandback/><hammoveo/><hamlargemod/><hamwavy/></hamnosys_manual></hns_sign>',
    "easy":      '<hns_sign gloss="easy"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hampinchall/><hamextfingero/><hampalmu/><hamstomach/><hamlrat/><hamclose/><hamparbegin/><hamreplace/><hamfinger2345/><hamthumboutmod/><hamextfingero/><hampalmu/><hamparend/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "difficult": '<hns_sign gloss="difficult"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamfinger23/><hamthumbacrossmod/><hamextfingerul/><hampalmd/><hamshoulders/><hamparbegin/><hammoveu/><hamsmallmod/><hamreplace/><hammoved/><hamsmallmod/><hamparend/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    # ── Russian keywords → same signs ────────────────────────────────────────
    "привет":     "hello", "здравствуйте": "hello", "сәлем": "hello",
    "хорошо":     "good",  "жақсы": "good",
    "да":         "yes",   "иә": "yes",
    "нет":        "no",    "жоқ": "no",
    "пожалуйста": "please",
    "понятно":    "understand", "понял": "understand",
    "знаю":       "know",  "знать": "know",
    "помощь":     "help",  "помоги": "help",
    "сейчас":     "now",   "сейчас": "now",
    "имя":        "name",
    "иди":        "go",    "идти": "go",
    "приди":      "come",  "прийти": "come",
    "есть":       "eat",   "пить": "drink",
    "спать":      "sleep", "думать": "think",
    "читать":     "read",  "учить": "learn",
    "учить":      "teach", "отвечать": "answer",
    "звонить":    "call",  "отправить": "send",
    "открыть":    "open",  "закрыть": "close",
    "закончить":  "finish",
    "утро":       "morning", "вечер": "evening",
    "день":       "day",   "ночь": "night",
    "грустно":    "sad",   "люблю": "love",
    "нравится":   "like",  "смеяться": "laugh",
    "плакать":    "cry",   "плохо": "bad",
    "большой":    "big",   "маленький": "small",
    "медленно":   "slow",  "легко": "easy",
    "трудно":     "difficult",
}

# Resolve string aliases (RU → EN key)
for _k, _v in list(_SIGN_MAP.items()):
    if isinstance(_v, str) and _v in _SIGN_MAP:
        _SIGN_MAP[_k] = _SIGN_MAP[_v]

# Pool for fallback — all keys with actual SiGML content
_POOL = [k for k, v in _SIGN_MAP.items() if isinstance(v, str) and v.startswith("<hns_sign")]


def text_to_sigml(text: str) -> str:
    """
    Convert a text segment to a SiGML string.
    Matches known keywords; falls back to deterministic pool selection.
    """
    words = text.lower().split()
    signs: list[str] = []

    for word in words:
        clean = word.strip(".,!?;:\"'()-…")
        entry = _SIGN_MAP.get(clean)
        if isinstance(entry, str) and entry.startswith("<hns_sign"):
            signs.append(entry)

    if not signs:
        idx = int(hashlib.md5(text.encode()).hexdigest(), 16) % len(_POOL)
        signs.append(_SIGN_MAP[_POOL[idx]])

    return f'<sigml>{"".join(signs)}</sigml>'

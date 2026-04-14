"""
SiGML lookup: maps Russian/English keywords to SiGML sign fragments.
Returns a multi-sign SiGML string for a given text segment.
"""

import hashlib

# Each entry: keyword (lowercase) -> hns_sign XML element (validated against CWASA HtoG)
# Signs sourced from ISL (Indian SL) dataset via CWASA HamNoSys format.

_SIGN_MAP: dict[str, str] = {
    # English
    "hello": '<hns_sign gloss="hello"><hamnosys_nonmanual><hnm_mouthpicture picture="hVlU"/></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hambetween/><hamfinger2345/><hamextfingeru/><hampalmd/><hamshouldertop/><hamlrat/><hamarmextended/><hamswinging/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "good": '<hns_sign gloss="good"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchopen/><hamextfingeru/><hampalml/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "yes": '<hns_sign gloss="yes"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingero/><hampalmd/><hamstomach/><hamlrat/><hamclose/><hamnodding/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "no": '<hns_sign gloss="no"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinch12/><hamfingerstraightmod/><hamindexfinger/><hammiddlefinger/><hamextfingerul/><hampalmd/><hamshoulders/><hamlrat/><hamplus/><hamcee12/><hamindexfinger/><hammiddlefinger/><hamextfingerul/><hampalmd/><hamshoulders/><hamlrat/></hamnosys_manual></hns_sign>',
    "please": '<hns_sign gloss="please"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchall/><hamextfingero/><hampalmu/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "understand": '<hns_sign gloss="understand"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrat/><hamclose/><hamreplace/><hamfinger2/><hamthumboutmod/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "know": '<hns_sign gloss="know"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamfingerstraightmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrbeside/><hamseqbegin/><hammoveor/><hammoveil/><hamseqend/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    "not": '<hns_sign gloss="not"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamcee12/><hamindexfinger/><hammiddlefinger/><hamextfingeru/><hampalmdl/><hamshoulders/><hamclose/><hamreplace/><hampinch12/><hamindexfinger/><hammiddlefinger/><hamextfingeru/><hampalmdl/><hamshoulders/><hamclose/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "now": '<hns_sign gloss="now"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamextfingerdl/><hampalmul/><hambetween/><hampalmr/><hamchest/><hammoved/><hamlargemod/></hamnosys_manual></hns_sign>',
    "name": '<hns_sign gloss="name"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger23/><hamthumbacrossmod/><hamextfingerl/><hambetween/><hamextfingerul/><hampalmd/><hamforehead/><hamparbegin/><hammoveo/><hamreplace/><hamextfingero/><hampalmd/><hamparend/></hamnosys_manual></hns_sign>',
    "help": '<hns_sign gloss="help"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmpar/><hamparbegin/><hamfist/><hamthumboutmod/><hamplus/><hamflathand/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingerl/><hampalml/><hamplus/><hamextfingeror/><hampalmu/><hamparend/><hamparbegin/><hampalm/><hamplus/><hampinkyside/><hamparend/><hamtouch/><hammovei/></hamnosys_manual></hns_sign>',
    "announce": '<hns_sign gloss="announce"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmpar/><hampinchall/><hamextfingeru/><hampalml/><hamparbegin/><hamfingertip/><hamthumb/><hamindexfinger/><hamplus/><hamfingertip/><hamthumb/><hamindexfinger/><hamparend/><hamtouch/><hamchin/><hamparbegin/><hamreplace/><hamfinger2345/><hamextfingeruo/><hampalmd/><hamclose/><hamshoulders/><hamparend/></hamnosys_manual></hns_sign>',
    # Russian keywords -> same signs (concept mapping)
    "привет": '<hns_sign gloss="hello"><hamnosys_nonmanual><hnm_mouthpicture picture="hVlU"/></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hambetween/><hamfinger2345/><hamextfingeru/><hampalmd/><hamshouldertop/><hamlrat/><hamarmextended/><hamswinging/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "хорошо": '<hns_sign gloss="good"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchopen/><hamextfingeru/><hampalml/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "да": '<hns_sign gloss="yes"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingero/><hampalmd/><hamstomach/><hamlrat/><hamclose/><hamnodding/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "нет": '<hns_sign gloss="no"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinch12/><hamfingerstraightmod/><hamindexfinger/><hammiddlefinger/><hamextfingerul/><hampalmd/><hamshoulders/><hamlrat/></hamnosys_manual></hns_sign>',
    "пожалуйста": '<hns_sign gloss="please"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchall/><hamextfingero/><hampalmu/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "понятно": '<hns_sign gloss="understand"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrat/><hamclose/><hamreplace/><hamfinger2/><hamthumboutmod/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "знаю": '<hns_sign gloss="know"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamfingerstraightmod/><hamextfingeru/><hampalml/><hamforehead/><hamlrbeside/><hamseqbegin/><hammoveor/><hammoveil/><hamseqend/><hamrepeatfromstartseveral/></hamnosys_manual></hns_sign>',
    "помощь": '<hns_sign gloss="help"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmpar/><hamparbegin/><hamfist/><hamthumboutmod/><hamplus/><hamflathand/><hamthumboutmod/><hamparend/><hamparbegin/><hamextfingerl/><hampalml/><hamplus/><hamextfingeror/><hampalmu/><hamparend/><hamparbegin/><hampalm/><hamplus/><hampinkyside/><hamparend/><hamtouch/><hammovei/></hamnosys_manual></hns_sign>',
    "сейчас": '<hns_sign gloss="now"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamsymmlr/><hamflathand/><hamextfingerdl/><hampalmul/><hambetween/><hampalmr/><hamchest/><hammoved/><hamlargemod/></hamnosys_manual></hns_sign>',
    "имя": '<hns_sign gloss="name"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfinger23/><hamthumbacrossmod/><hamextfingerl/><hambetween/><hamextfingerul/><hampalmd/><hamforehead/><hamparbegin/><hammoveo/><hamreplace/><hamextfingero/><hampalmd/><hamparend/></hamnosys_manual></hns_sign>',
    # Kazakh
    "сәлем": '<hns_sign gloss="hello"><hamnosys_nonmanual><hnm_mouthpicture picture="hVlU"/></hamnosys_nonmanual><hamnosys_manual><hamflathand/><hamthumboutmod/><hambetween/><hamfinger2345/><hamextfingeru/><hampalmd/><hamshouldertop/><hamlrat/><hamarmextended/><hamswinging/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "жақсы": '<hns_sign gloss="good"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinchopen/><hamextfingeru/><hampalml/><hamchest/><hamlrat/></hamnosys_manual></hns_sign>',
    "иә": '<hns_sign gloss="yes"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hamfist/><hamthumboutmod/><hamextfingero/><hampalmd/><hamstomach/><hamlrat/><hamclose/><hamnodding/><hamrepeatfromstart/></hamnosys_manual></hns_sign>',
    "жоқ": '<hns_sign gloss="no"><hamnosys_nonmanual></hamnosys_nonmanual><hamnosys_manual><hampinch12/><hamfingerstraightmod/><hamindexfinger/><hammiddlefinger/><hamextfingerul/><hampalmd/><hamshoulders/><hamlrat/></hamnosys_manual></hns_sign>',
}

# Pool of valid signs used for variety when no keyword match found.
# Deterministic by text hash so same phrase always gets same sign.
_POOL = [
    "hello", "good", "yes", "no", "please", "understand",
    "know", "not", "now", "name", "help", "announce",
]


def text_to_sigml(text: str) -> str:
    """
    Convert a text segment to a SiGML string.
    - If keywords are found in the text, use those signs.
    - Otherwise pick a sign from the pool deterministically by text hash,
      so the avatar always animates with variety instead of one repeated gesture.
    """
    words = text.lower().split()
    signs: list[str] = []

    for word in words:
        clean = word.strip(".,!?;:\"'()-")
        if clean in _SIGN_MAP:
            signs.append(_SIGN_MAP[clean])

    if not signs:
        # Pick deterministically from pool — same text = same sign, different texts vary
        idx = int(hashlib.md5(text.encode()).hexdigest(), 16) % len(_POOL)
        signs.append(_SIGN_MAP[_POOL[idx]])

    body = "".join(signs)
    return f'<sigml>{body}</sigml>'

# -*- coding: utf-8 -*-

import re
import unicodedata

_TECH = {
    "4k","8k","uhd","fhd","hd","2160p","1080p","720p","3840p","4320p",
    "hdr","hdr10","dolby","atmos","hevc","h265","h264","avc","top","vip",
    "subs","sub","dub","dubs","raw","bluray","bdrip","brrip","hdrip","webrip","webdl","x264","x265","multi","audio","vod","movie","movies","series","tv",
    "ar","en","tr","s","do","fr","de","es","it","pl","nl","ru","pt","br","us","uk","eg","ksa","uae","der","ger","deu","lat","ara","eng","tur","kor","jpn","ind","arabic","english","turkish"," مترجم","مدبلج"
}

def _normalize_unicode_digits(value):
    text=str(value or "")
    out=[]
    for ch in text:
        try:
            if unicodedata.category(ch)=="Nd":
                out.append(str(unicodedata.digit(ch)))
            else:
                out.append(ch)
        except Exception:
            out.append(ch)
    return "".join(out)


def clean_title(value):
    text = _normalize_unicode_digits(value).strip()

    # --- DODATO ZA UKLANJANJE |MULTI| i sličnih prefiksa ---
    # Ovo hvata |MULTI|, | MULTI |, |  MULTI  |, |NL|, | UCL |, itd.
    text = re.sub(r'^\|+\s*[^|]+\s*\|+\s*', '', text)
    text = re.sub(r'^\┃+\s*[^┃]+\s*┃+\s*', '', text)
    # -------------------------------------------------------
    # 1. Strip purely decorative edge symbols/emoji
    text = re.sub(r"^[\s\u2600-\u27ff\u2b00-\u2bff\U0001F000-\U0001FAFF]+", "", text)
    text = re.sub(r"[\s\u2600-\u27ff\u2b00-\u2bff\U0001F000-\U0001FAFF]+$", "", text)

    # 2. Prvo ukloni | ... | prefiks (bilo koji tekst između dva |)
    # Ovo hvata |MULTI|, | MULTI |, |NL|, | UCL | itd.
    text = re.sub(r'^\|+\s*[^|]+\s*\|+\s*', '', text)
    text = re.sub(r'^\|\s*[^|]+\s*\|\s*', '', text)

    # 3. Zatim ukloni tehničke prefikse (MULTI, NL, DE, itd.) ako su ostali
    # Ovo hvata slučajeve gde je | već uklonjen, ali je ostao MULTI
    text = re.sub(r'^(?:MULTI|NL|DE|FR|IT|ES|EN|AR|EX-YU|UHD|4K|FHD|HD|SD|H265|HEVC|MOVIES?|SERIES|TV|UCL|PPV)\s*[-:|]?\s*', '', text, flags=re.I)

    # 4. Common routing/service labels wrapped in braces/brackets are not titles.
    text = re.sub(
        r"^[\[{(]\s*(?:4K|8K|UHD|FHD|HD|AR|EN|ARA|ENG|VIP|TOP|NEW|MOVIE|MOVIES|SERIES|TV|MULTI|NL|DE|FR|IT|ES)(?:[-_ /|]+(?:4K|8K|UHD|FHD|HD|AR|EN|ARA|ENG|VIP|TOP|NEW|SUBS?|DUBS?))*\s*[\]})]\s*[-:|]*\s*",
        "", text, flags=re.I)

    # 5. Strip provider routing prefixes like "AR - ", "EN - "
    m = re.match(r"^([A-Z0-9]{2,6}(?:[-_][A-Z0-9]{1,6})*)\s+-\s+(.+)$", text)
    if m and ("-" in m.group(1) or "_" in m.group(1) or re.search(r"[\u0600-\u06ff]", m.group(2))):
        text = m.group(2).strip()

    # 6. Strip technical tags in brackets/parentheses
    text = re.sub(r"\[(?:[^\]]*?(?:4K|8K|UHD|FHD|HD|2160P|1080P|720P|HDR|DOLBY|SUB|DUB)[^\]]*?)\]", " ", text, flags=re.I)
    text = re.sub(r"\((?:US|USA|UK|GB|EG|EGY|KSA|SA|UAE|AE|KR|KOR|TR|TUR|JP|JPN|CN|CHN|IN|IND|AR|EN|SUBS?|DUB|DUBBED|مترجم|مدبلج)\)", " ", text, flags=re.I)

    # 7. Strip year in parentheses
    text = re.sub(r"\((?:19|20)\d{2}\)", " ", text)

    # 8. Split by separators and remove technical-only leading parts
    parts = re.split(r"\s[-|:]\s", text)
    while len(parts) > 1:
        first = re.sub(r"[^\w+]+", " ", parts[0], flags=re.UNICODE).strip().casefold()
        toks = [t for t in first.split() if t]
        known = sum(1 for t in toks if t in _TECH or re.match(r"^(?:4k|8k|\d{3,4}p)$", t))
        if len(toks) >= 2 and known >= max(2, len(toks) - 1):
            parts.pop(0)
        else:
            break
    text = " - ".join(parts)

    # 9. Strip known technical words
    text = re.sub(
        r"\b(?:4K|8K|UHD|FHD|HD|2160P|1080P|720P|3840P|4320P|HDR10?|DOLBY|ATMOS|HEVC|X264|X265|BLU[ ._-]?RAY|BDRIP|BRRIP|HDRIP|WEB[ ._-]?(?:DL|RIP)|MULTI[ ._-]?AUDIO|H\.?(?:264|265)|AR[-_ ]?SUBS?|SUBS?|DUBBED|DUB|RAW)\b",
        " ", text, flags=re.I)

    # 10. Strip routing prefixes like "AR-AS-D |", "VIP_MOVIES:"
    text = re.sub(
        r"^(?:#+\s*)?(?:AR|EN|BE|UK|US|EG|KSA|TOP|VIP|MOVIES?|SERIES|TV)(?:[-_ ](?:SUBS?|DUBS?|RAW|4K|8K|UHD|HD|TOP))*\s*[:|\-]+\s*",
        "", text, flags=re.I)

    # 11. Strip residual provider/routing prefixes
    _route = r"(?:DER|GER|DEU|ENG|ARA|LAT|AR|EN|TR|DO|FR|ES|IT|PL|NL|RU|PT|BR|US|UK|EG|KSA|UAE|SUBS?|DUBS?|RAW|4K|8K|UHD|FHD|HD|VIP|TOP)"
    text = re.sub(r"^(?:" + _route + r")(?:[-_/](?:" + _route + r")){0,4}\s*(?:[|｜:/-]+)\s*(?=.+)", "", text, flags=re.I)

    # 12. Broken/incomplete country suffixes
    text = re.sub(r"\s*[\[(]\s*(?:[A-Z]{2,3}|USA|UAE|KSA)\s*[\])]?$", " ", text, flags=re.I)

    # 13. Cleanup extra spaces and dangling characters
    text = re.sub(r"\s+", " ", text).strip(" -_|:.()[]{}")

    # 14. Ako je ostao samo "MULTI" ili slično, vrati original
    if text.upper() in _TECH:
        return str(value or "").strip()

    return text or str(value or "").strip()


def tmdb_search_title(value):
    """Aggressive SEARCH-ONLY title cleaner.

    IMPORTANT: this function must never be used as a catalogue/cache identity.
    The provider's raw label stays untouched for UI and persistent artwork keys.
    Only TMDB/Fanart matching gets this normalized title.
    """
    text=_normalize_unicode_digits(value).strip()
    if not text:
        return ""
    # Decorative edge glyphs / emoji / bullets.
    text=re.sub(r"^[\s\u2600-\u27ff\u2b00-\u2bff\U0001F000-\U0001FAFF★☆✦✧◆◇●○■□▶▷►]+", "", text)
    text=re.sub(r"[\s\u2600-\u27ff\u2b00-\u2bff\U0001F000-\U0001FAFF★☆✦✧◆◇●○■□▶▷►]+$", "", text)
    # Leading provider/platform route labels. Keep this search-only and require a
    # separator so real titles such as X-Men, Se7en or F1 are never damaged.
    edge=r"(?:AMZ|AMZN|NF|NETFLIX|AS|A\+|D\+|DSNP|DISNEY\+|APTV|APPLETV\+|HBO|MAX|HMAX|PM|PRIME|VIP|TOP|VOD|MOVIES?|SERIES|TV|4K|8K|UHD|FHD|HD|AR|ARA|EN|ENG|TR|FR|DE|ES|IT|SUBS?|DUBS?|RAW)"
    # Bracketed tags on either edge.
    text=re.sub(r"^\s*[\[{(]\s*"+edge+r"(?:\s*[-_/|+]\s*"+edge+r")*\s*[\]})]\s*[-:|┃]*\s*", "", text, flags=re.I)
    text=re.sub(r"\s*[-:|┃]*\s*[\[{(]\s*"+edge+r"(?:\s*[-_/|+]\s*"+edge+r")*\s*[\]})]\s*$", "", text, flags=re.I)
    # Plain edge tags: "NF - Title", "D+ | Title", "Title | AMZ".
    for _ in range(3):
        old=text
        text=re.sub(r"^\s*"+edge+r"(?:\s*[-_/+]\s*"+edge+r"){0,4}\s*(?:[-:|┃]+)\s*(?=\S)", "", text, flags=re.I)
        text=re.sub(r"\s*(?:[-:|┃]+)\s*"+edge+r"(?:\s*[-_/+]\s*"+edge+r"){0,4}\s*$", "", text, flags=re.I)
        if text==old: break
    # Year/quality/language decorations at the edges are search noise.
    text=re.sub(r"\s*[\[(]\s*(?:19|20)\d{2}\s*[\])]\s*$", " ", text)
    text=re.sub(r"\s*(?:[-|┃:]+)\s*(?:19|20)\d{2}\s*$", " ", text)
    text=re.sub(r"\s*(?:[-|┃:/]+)\s*(?:4K|8K|UHD|FHD|HD|2160P|1080P|720P|HDR10?|DOLBY|ATMOS|HEVC|H\.?26[45]|X26[45]|WEB[ ._-]?(?:DL|RIP)|BLU[ ._-]?RAY|SUBS?|DUBBED|DUB|RAW|AR|EN|ARA|ENG)\s*$", " ", text, flags=re.I)
    # Generic portal codes are stripped only when isolated by a strong separator.
    text=re.sub(r"^\s*[A-Z0-9+]{2,6}\s+(?:[-|┃:])\s+(?=\S)", "", text)
    text=re.sub(r"\s+(?:[-|┃:])\s+[A-Z0-9+]{2,6}\s*$", "", text)
    # Existing safe search cleanup.
    text=re.sub(r"^(.+?)[,\s]+the$",lambda m:"The "+m.group(1).strip(),text,flags=re.I)
    text=re.sub(r"^(?:\s*[^|┃]{0,40}[|┃])+\s*","",text)
    text=re.sub(r"\([^)]*\)"," ",text)
    text=re.sub(r"\[[^\]]*\]"," ",text)
    text=re.sub(r"\b(?:4K|8K|UHD|FHD|HD|2160P|1080P|720P|HDR10?|DOLBY|ATMOS|HEVC|H\.?26[45]|X26[45]|BLU[ ._-]?RAY|WEB[ ._-]?(?:DL|RIP)|SUBS?|DUBBED|DUB|RAW|VIP|TOP|MOVIES?|SERIES|TV)\b"," ",text,flags=re.I)
    text=re.sub(r"\b(?:مترجم|مدبلج|حصري|جديد|قريبا|قريباً|قريبًا)\b"," ",text,flags=re.I)
    text=re.sub(r"[._'*]+"," ",text)
    text=re.sub(r"\s+"," ",text).strip(" -_|:.")
    return text or clean_title(value)

def tmdb_search_aliases(value):
    """Return Xstreamity-style search aliases, preserving the full cleaned title.

    For mixed-script catalogue names, Xstreamity drops non-ASCII text during
    search normalization. We keep BOTH forms so matching is broader without
    changing the title shown to the user.
    """
    full=tmdb_search_title(value)
    out=[]
    has_ascii=bool(re.search(r"[A-Za-z]",full))
    has_non_ascii=bool(re.search(r"[^\x00-\x7f]",full))
    if has_ascii and has_non_ascii:
        latin=unicodedata.normalize("NFKD",full).encode("ascii","ignore").decode("ascii")
        latin=re.sub(r"\s+"," ",latin).strip(" -_|:.")
        if latin:
            out.append(latin)
    if full and full not in out:
        out.append(full)
    return out



def catalogue_title(value):
    """Visible/search title with catalogue branding and year decoration removed.

    'Pure' is treated as branding only when another meaningful title remains.
    An item literally named 'Pure' is preserved.
    """
    text=clean_title(value)
    text=re.sub(r"[\[(]\s*(?:19|20)\d{2}\s*[\])]", " ", text)
    text=re.sub(r"\b(?:19|20)\d{2}\b", " ", text)
    # Remove standalone PURE only if other meaningful content survives.
    without=re.sub(r"(?iu)(?<!\w)pure(?!\w)", " ", text)
    without=re.sub(r"\s+"," ",without).strip(" -_|:.()[]")
    meaningful=re.sub(r"[\W_]+","",without,flags=re.UNICODE)
    if len(meaningful)>=2:
        text=without
    text=re.sub(r"\s+"," ",text).strip(" -_|:.()[]")
    return text or clean_title(value)


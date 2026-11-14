# -*- coding: utf-8 -*-
#
# rich_metadata.py - Nezavisan rich metadata modul za CiefpSfiles
# (TMDB search sa prevodom, OMDb rejting, placeholders, detect_non_tmdb)
#
from __future__ import print_function
import os
import re
import ssl
import json
import time
import threading
import urllib.request
import urllib.parse

from .config import config
from .metadata import _fetch_json, _get_api_key, _get_omdb_key, _get_cache_dir
# ---------- PLACEHOLDERS ----------
def _icon_path(name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", name)

PLACEHOLDER        = _icon_path("placeholder.png")
PLACEHOLDER_EPG    = _icon_path("epg_placeholder.png")
PLACEHOLDER_MOVIE  = _icon_path("movie.png")
PLACEHOLDER_SERIES = _icon_path("series.png")
PLACEHOLDER_SPORT  = _icon_path("sport.png")
PLACEHOLDER_MUSIC  = _icon_path("music.png")
PLACEHOLDER_NEWS   = _icon_path("news.png")
PLACEHOLDER_KIDS   = _icon_path("kids.png")
PLACEHOLDER_DOCU   = _icon_path("docu.png")


def get_placeholder(path, default=None):
    """Vrati path ako postoji, inače default (ili PLACEHOLDER)."""
    if path and os.path.exists(path):
        return path
    return default if default else PLACEHOLDER


def get_epg_placeholder():
    """Vrati EPG placeholder ili glavni placeholder ako epg_placeholder.png ne postoji."""
    if os.path.exists(PLACEHOLDER_EPG):
        return PLACEHOLDER_EPG
    return PLACEHOLDER


def choose_placeholder(genres, epg=False):
    if not genres:
        return get_epg_placeholder() if epg else PLACEHOLDER
    g = " ".join(genres).lower()
    if any(k in g for k in ("sport", "sports")):
        return get_placeholder(PLACEHOLDER_SPORT,
                               get_epg_placeholder() if epg else PLACEHOLDER)
    if any(k in g for k in ("music", "musical")):
        return get_placeholder(PLACEHOLDER_MUSIC,
                               get_epg_placeholder() if epg else PLACEHOLDER)
    if any(k in g for k in ("news", "weather")):
        return get_placeholder(PLACEHOLDER_NEWS,
                               get_epg_placeholder() if epg else PLACEHOLDER)
    if any(k in g for k in ("animation", "family", "kids")):
        return get_placeholder(PLACEHOLDER_KIDS,
                               get_epg_placeholder() if epg else PLACEHOLDER)
    if any(k in g for k in ("documentary", "documentaries")):
        return get_placeholder(PLACEHOLDER_DOCU,
                               get_epg_placeholder() if epg else PLACEHOLDER)
    return get_epg_placeholder() if epg else PLACEHOLDER


# ---------- GENERIC TITLES ----------
GENERIC_TITLES = {
    "vesti", "vijesti", "dnevnik", "program", "info",
    "informativni program", "jutarnji program", "večernji program",
    "dnevnik 1", "dnevnik 2", "sat", "vreme", "prognoza",
    "report", "reports", "sport", "emisija",
    "razgovor", "intervju", "talk show",
    "news", "weather", "sports", "info", "program",
    "morning show", "evening news", "breaking news",
    "nachrichten", "wetter", "programm",
    "actualités", "météo", "journal",
    "notizie", "meteo", "telegiornale",
    "noticias", "tiempo", "informativos",
    "zprávy", "počasí", "správy", "počasie",
}


def is_generic_title(title):
    if not title:
        return True
    t = title.lower().strip()
    if t in GENERIC_TITLES:
        return True
    if len(t) < 4:
        return True
    return False


# ---------- detect_non_tmdb ----------
def _kw_match(combo, keywords):
    for kw in keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', combo):
            return kw
    return None

def detect_non_tmdb(title, description, epg=False):
    t = (title or "").lower()
    d = (description or "").lower()
    combo = t + " " + d

    sport_kw = (
        "sport", "sports", "football", "fudbal", "soccer", "nogomet",
        "tennis", "tenis", "basket", "basketball", "košarka", "kosarka",
        "nba", "nfl", "formula 1", "f1", "formula", "formule",
        "moto gp", "motogp", "moto2", "moto3", "olympic", "olimpijada",
        "atletika", "utakmica", "utakmice", "match", "liga", "extraliga",
        "kup", "cup", "champions league", "premier league", "bundesliga",
        "serie a", "la liga", "handball", "rukomet", "hokej", "hockey",
        "volejbal", "volleyball", "odbojka", "swimming", "plivanje",
        "ski", "skijanje", "cyklistika", "cycling", "biciklizam",
        "race", "utrka", "turnaj", "tournament", "turnir",
    )
    music_kw = (
        "music", "musical", "muzika", "glazba", "hudba", "concert",
        "koncert", "live concert", "festival", "mtv", "vh1",
        "opera", "opereta",
    )
    news_kw = (
        "news", "vesti", "novosti", "nachrichten", "actualités",
        "noticias", "telegiornale", "dnevnik", "tagesschau",
        "správy", "zprávy", "reportáž", "newstime",
        "jutarnji program", "informativni", "program",
    )
    kids_kw = (
        "kids", "dečiji", "za decu", "for kids", "children's",
        "child's", "kinder", "infantile", "pour enfants",
        "per bambini", "para niños",
    )
    documentary_kw = (
        "documentary", "dokument", "dokumentarni", "dokumentární",
        "dokumentarna",
    )

    fallback = get_epg_placeholder() if epg else PLACEHOLDER

    hit = _kw_match(combo, sport_kw)
    if hit:
        return True, get_placeholder(PLACEHOLDER_SPORT, fallback)
    hit = _kw_match(combo, music_kw)
    if hit:
        return True, get_placeholder(PLACEHOLDER_MUSIC, fallback)
    hit = _kw_match(combo, news_kw)
    if hit:
        return True, get_placeholder(PLACEHOLDER_NEWS, fallback)
    hit = _kw_match(combo, kids_kw)
    if hit:
        return True, get_placeholder(PLACEHOLDER_KIDS, fallback)
    hit = _kw_match(combo, documentary_kw)
    if hit:
        return True, get_placeholder(PLACEHOLDER_DOCU, fallback)
    return False, None



# ---------- TMDB SEARCH (sa prevodom naslova preko Translator-a) ----------
def _tmdb_search_multi(title, year, api_key, language="en-US"):
    if not api_key:
        return None, None
    try:
        params = {
            "api_key": api_key,
            "query": title,
            "language": language,
            "include_adult": "false",
        }
        if year:
            params["year"] = year
        url = "https://api.themoviedb.org/3/search/multi?" + urllib.parse.urlencode(params)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        results = [r for r in data.get("results", [])
                   if r.get("media_type") in ("movie", "tv")]
        if not results:
            return None, None
        if year:
            for c in results:
                c_year = (c.get("release_date") or c.get("first_air_date") or "")[:4]
                if c_year == str(year):
                    return c, c["media_type"]
        best = results[0]
        return best, best["media_type"]
    except Exception as e:
        print("[rich_metadata] multi search error:", e)
        return None, None


# Koristi metadata.translate_text_async sinhrono preko threading.Event
def _translate_title_sync(title):
    """Sinhrono prevede naslov na engleski koristeći metadata.translate_text_async."""
    if not title:
        return None
    # Ako je naslov već skoro sigurno engleski (ASCII), ne prevodimo
    ascii_count = sum(1 for c in title if ord(c) < 128)
    if len(title) > 0 and (ascii_count / float(len(title))) > 0.95:
        return None
    # Prevod preko metadata.translate_text_async
    from .metadata import translate_text_async
    result = {"done": False, "success": False, "text": None}
    event = threading.Event()

    def cb(success, text):
        result["done"] = True
        result["success"] = success
        result["text"] = text
        event.set()

    try:
        translate_text_async(title, cb)
        # Čekamo max 15 sekundi
        event.wait(timeout=15)
    except Exception as e:
        print("[rich_metadata] translate title error:", e)
        return None

    if result["success"] and result["text"]:
        translated = result["text"].strip().strip('"').strip("'")
        if translated.lower().startswith("title:"):
            translated = translated[6:].strip()
        if translated.lower().strip() == title.lower().strip():
            return None
        return translated
    return None


def tmdb_search_with_translation(title, year, api_key, language="en-US"):
    """Pretraga TMDB sa automatskim prevodom naslova na engleski."""
    result, media_type = _tmdb_search_multi(title, year, api_key, language)
    if result:
        return result, media_type
    # Pokušaj sa prevodom
    english_title = _translate_title_sync(title)
    if english_title and english_title.lower() != title.lower():
        result, media_type = _tmdb_search_multi(english_title, year, api_key, language)
        if result:
            return result, media_type
    return None, None


def tmdb_details(media_id, media_type, api_key, language="en-US"):
    try:
        url = (f"https://api.themoviedb.org/3/{media_type}/{media_id}"
               f"?api_key={api_key}&language={language}"
               f"&append_to_response=credits")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print("[rich_metadata] details error:", e)
        return None


def omdb_rating(media_info, media_type, api_key):
    if not api_key:
        return None
    title = media_info.get("title") if media_type == "movie" else media_info.get("name")
    year = ((media_info.get("release_date") or "")[:4] if media_type == "movie"
            else (media_info.get("first_air_date") or "")[:4])
    if not title:
        return None
    try:
        params = {"apikey": api_key, "t": title, "r": "json"}
        if year:
            params["y"] = year
        url = "http://www.omdbapi.com/?" + urllib.parse.urlencode(params)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if data.get("Response") == "True" and data.get("imdbRating") not in ("N/A", ""):
            return data.get("imdbRating")
    except Exception as e:
        print("[rich_metadata] omdb error:", e)
    return None


# ---------- TMDB PERSON (za buduće Filmography / Cast explore) ----------
def tmdb_search_person(name, api_key, language="en-US"):
    if not api_key:
        return None
    try:
        params = {"api_key": api_key, "query": name, "language": language}
        url = "https://api.themoviedb.org/3/search/person?" + urllib.parse.urlencode(params)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        results = data.get("results", [])
        return results[0] if results else None
    except Exception as e:
        print("[rich_metadata] person search error:", e)
        return None


def tmdb_person_details(person_id, api_key, language="en-US"):
    try:
        url = (f"https://api.themoviedb.org/3/person/{person_id}"
               f"?api_key={api_key}&language={language}"
               f"&append_to_response=movie_credits,tv_credits,external_ids")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print("[rich_metadata] person details error:", e)
        return None


# ---------- IMAGE DOWNLOAD ----------
def download_image_sync(url, filename):
    """Preuzme sliku u keš folder. Vraća path ili None."""
    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, filename)
    if os.path.exists(path):
        return path
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            with open(path, 'wb') as f:
                f.write(resp.read())
        return path
    except Exception as e:
        print("[rich_metadata] image download error:", e)
        return None


def download_poster_async(poster_path, media_id, media_type, callback):
    """Asinhrono preuzme poster i pozove callback(path_ili_None)."""
    def worker():
        if not poster_path or not media_id:
            callback(None)
            return
        fname = f"poster_{media_type}_{media_id}_{os.path.basename(poster_path)}"
        url = "https://image.tmdb.org/t/p/w500" + poster_path
        path = download_image_sync(url, fname)
        callback(path)

    threading.Thread(target=worker, daemon=True).start()


def download_person_photo_async(profile_path, person_id, callback):
    def worker():
        if not profile_path or not person_id:
            callback(None)
            return
        fname = f"person_{person_id}_{os.path.basename(profile_path)}"
        url = "https://image.tmdb.org/t/p/w500" + profile_path
        path = download_image_sync(url, fname)
        callback(path)

    threading.Thread(target=worker, daemon=True).start()


# ---------- GETTERS za ključeve / jezik (iz CiefpSfiles config) ----------
def get_tmdb_key():
    return _get_api_key()


def get_omdb_key():
    return _get_omdb_key()


def get_language():
    try:
        return config.plugins.ciefpsfiles.tmdb_language.value
    except Exception:
        return "en-US"
# -*- coding: utf-8 -*-
import os
import json
import urllib.parse
import threading

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import ssl

from .config import config
from .paths import TMDB_KEY_FILE, OMDB_KEY_FILE, POSTERS_CACHE_DIR


def _get_cache_dir():
    if not os.path.exists(POSTERS_CACHE_DIR):
        try:
            os.makedirs(POSTERS_CACHE_DIR)
        except Exception:
            pass
    return POSTERS_CACHE_DIR


def _get_api_key():
    # 1. Iz Settings-a
    key = config.plugins.ciefpsfiles.tmdb_api_key.value
    if key:
        return key.strip()
    # 2. Iz fajla
    if os.path.exists(TMDB_KEY_FILE):
        try:
            with open(TMDB_KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def _get_omdb_key():
    # 1. Iz Settings-a
    key = config.plugins.ciefpsfiles.omdb_api_key.value
    if key:
        return key.strip()
    # 2. Iz fajla
    if os.path.exists(OMDB_KEY_FILE):
        try:
            with open(OMDB_KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""

def _fetch_json(url):
    import ssl
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[CiefpSfiles] JSON Fetch Error: {e}")
        return None


def _download_image(url, filename):
    import ssl
    import urllib.request
    path = os.path.join(_get_cache_dir(), filename)
    if os.path.exists(path):
        return path

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            with open(path, 'wb') as f:
                f.write(response.read())
        return path
    except Exception as e:
        print(f"[CiefpSfiles] Image download error: {e}")
        return None


def fetch_metadata_async(title, media_type, callback):
    def worker():
        api_key = _get_api_key()
        if not api_key:
            callback(False, "TMDB API Key not found in tmdbapikey.txt")
            return
        import re
        search_title = title

        # 1. Uklanjamo prefikse kao što su "4K | ", "HD | ", "FHD | " itd.
        if "|" in search_title:
            search_title = search_title.split("|", 1)[1].strip()

        # 2. Uklanjamo prefikse u zagradama na početku, npr. "[HD] ", "[4K] "
        search_title = re.sub(r'^\[.*?\]\s*', '', search_title)

        # 3. Uklanjamo jezičke prefikse na početku, npr. "EN - ", "FR - ", "DE - ", "SR - ", "EX-YU - " itd.
        search_title = re.sub(r'^[A-Z]{2,5}\s*-\s*', '', search_title)

        # 4. Uklanjamo sufiksе u zagradama na kraju, npr. "[MULTI-SUB]", "[HD]", "[4K]"
        search_title = re.sub(r'\s*\[.*?\]\s*$', '', search_title).strip()

        # 5. PRVO ZAMENJUJEMO DONJE CRTE I TAČKE RAZMACIMA
        search_title = search_title.replace("_", " ").replace(".", " ")

        # 6. UKLANJAMO GODINU IZ ZAGRADA (npr. "Movie (2023)" -> "Movie")
        m = re.search(r'\((\d{4})\)', search_title)
        if m:
            search_title = search_title.replace(m.group(0), "").strip()

        # 7. UKLANJAMO GODINU SA KRAJA, SA ILI BEZ CRTICE (npr. "Movie 2024" ili "Movie - 2024" -> "Movie")
        search_title = re.sub(r'\s*-\s*(19|20)\d{2}\s*$', '', search_title).strip()
        search_title = re.sub(r'\s+(19|20)\d{2}\s*$', '', search_title).strip()

        # 8. Uklanjamo eventualne dodatne oznake kao što su "HD", "FHD", "4K" na kraju
        search_title = re.sub(r'\s+(HD|FHD|UHD|4K|SD|H265|HEVC)$', '', search_title, flags=re.IGNORECASE).strip()

        # 9. Uklanjamo višestruke razmake i prazne znakove
        search_title = re.sub(r'\s+', ' ', search_title).strip()

        # Ako je naslov ostao prazan nakon čišćenja, vrati grešku
        if not search_title:
            callback(False, "Invalid title after cleaning")
            return

        # Sada pretražujemo TMDB sa očišćenim naslovom
        try:
            query = urllib.parse.quote(search_title)
            url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={api_key}&query={query}&language=en-US"

            data = _fetch_json(url)

            if not data:
                callback(False, "TMDB request failed (Check network/SSL)")
                return

            results = data.get("results", [])
            if not results:
                callback(False, "Not found on TMDB")
                return

            result = results[0]
            tmdb_id = result.get("id")

            url_details = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}&language=en-US&append_to_response=credits"
            details = _fetch_json(url_details)

            if not details:
                callback(False, "TMDB details failed")
                return

            info = {}
            info["title"] = details.get("title") or details.get("name") or search_title
            info["year"] = (details.get("release_date") or details.get("first_air_date") or "")[:4]
            info["rating"] = details.get("vote_average", 0)
            info["plot"] = details.get("overview", "No plot available.")
            info["id"] = tmdb_id
            info["tmdb_id"] = tmdb_id

            genres = [g["name"] for g in details.get("genres", [])]
            info["genres"] = ", ".join(genres) if genres else "-"

            crew = details.get("credits", {}).get("crew", [])
            if media_type == "movie":
                directors = [c for c in crew if c.get("job") == "Director"]
                info["director"] = ", ".join([c["name"] for c in directors[:2]]) if directors else "-"
                # DODATO: Čuvamo sliku prvog režisera
                if directors:
                    info["director_profile_path"] = directors[0].get("profile_path")
                else:
                    info["director_profile_path"] = None
            else:
                creators = [c for c in crew if c.get("job") == "Creator"] # ili details.get("created_by")
                info["director"] = ", ".join([c["name"] for c in creators[:2]]) if creators else "-"
                info["director_profile_path"] = None # Serije obično nemaju sliku kreatora na isti način

            cast = details.get("credits", {}).get("cast", [])[:5]
            info["cast"] = ", ".join([c["name"] for c in cast]) if cast else "-"

            # DODATO: Uvek punimo cast_data (i za filmove i za serije)
            info["cast_data"] = []
            for c in cast:
                info["cast_data"].append({
                    "name": c.get("name"),
                    "profile_path": c.get("profile_path")
                })


            poster_path = details.get("poster_path")
            info["poster_path"] = None
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                poster_filename = f"{media_type}_{tmdb_id}.jpg"
                local_path = _download_image(poster_url, poster_filename)
                print(f"[CiefpSfiles] Poster downloaded to: {local_path}")
                if local_path and os.path.exists(local_path):
                    info["poster_path"] = local_path
                    print(f"[CiefpSfiles] Poster set to: {info['poster_path']}")
                else:
                    print(f"[CiefpSfiles] Poster download failed or file not exists")

            # DODAJ OVO:
            info["backdrop_path"] = details.get("backdrop_path")
            callback(True, info)

        except Exception as e:
            print(f"[CiefpSfiles] TMDB Error: {e}")
            callback(False, str(e))

    threading.Thread(target=worker, daemon=True).start()


def fetch_omdb_rating_async(title, year, callback):
    def worker():
        api_key = _get_omdb_key()
        if not api_key:
            callback(False, "OMDb Key not found")
            return

        try:
            params = {"apikey": api_key, "t": title, "r": "json"}
            if year:
                params["y"] = year
            query = urllib.parse.urlencode(params)
            url = f"http://www.omdbapi.com/?{query}"

            data = _fetch_json(url)
            if data and data.get("Response") == "True":
                rating = data.get("imdbRating")
                if rating and rating != "N/A":
                    callback(True, rating)
                    return
            callback(False, "N/A")
        except Exception as e:
            print(f"[CiefpSfiles] OMDb Error: {e}")
            callback(False, str(e))

    threading.Thread(target=worker, daemon=True).start()


def fetch_episode_metadata_async(tmdb_id, season_num, episode_num, callback):
    def worker():
        api_key = _get_api_key()
        if not api_key or not tmdb_id:
            callback(False, "Missing TMDB ID or API Key")
            return

        try:
            # Povlačimo detalje za epizodu
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}/episode/{episode_num}?api_key={api_key}&language=en-US"
            data = _fetch_json(url)
            if not data:
                callback(False, "Episode not found on TMDB")
                return

            info = {
                "title": data.get("name", f"Episode {episode_num}"),
                "plot": data.get("overview", "No description available."),
                "still_path": data.get("still_path"),
                "rating": data.get("vote_average", 0.0),
            }
            callback(True, info)
        except Exception as e:
            callback(False, str(e))

    threading.Thread(target=worker, daemon=True).start()

def translate_text_async(text, callback):
    def worker():
        try:
            # Importujemo Translator
            from ..components.translator import Translator

            tr = Translator()
            if not tr.is_available():
                callback(False, "Translator nije dostupan (API ključ ili requests nedostaju)")
                return

            # BEZBEDNO ČITANJE IZ CONFIG-A
            try:
                lang_code = config.plugins.ciefpsfiles.translate_language.value
            except Exception:
                lang_code = "sr"  # Ako pukne, podrazumevano prevedi na srpski

            translated = tr.translate(text, target_language=lang_code)

            if translated and translated != text:
                callback(True, translated)
            else:
                callback(False, "Translation returned original text or failed")
        except Exception as e:
            print(f"[CiefpSfiles] Translate Error: {e}")
            callback(False, str(e))

    threading.Thread(target=worker, daemon=True).start()

# -*- coding: utf-8 -*-
#
# paths.py - Centralno mesto za sve putanje u CiefpSfiles
#
import os

# Sistemski folder za sve podatke plugina
CONFIG_DIR = "/etc/enigma2/CiefpSfiles"

# Podfolderi
KEYS_DIR = os.path.join(CONFIG_DIR, "keys")
PLAYLIST_FILE = os.path.join(CONFIG_DIR, "playlist.txt")
CACHE_FILE = os.path.join(CONFIG_DIR, "portals_cache.json")
SUBTITLES_DIR = os.path.join(CONFIG_DIR, "subtitles")
POSTERS_CACHE_DIR = os.path.join(CONFIG_DIR, "posters")
EPG_CACHE_DIR = os.path.join(CONFIG_DIR, "epg")

# Putanje do API ključeva
TMDB_KEY_FILE = os.path.join(KEYS_DIR, "tmdbapikey.txt")
OMDB_KEY_FILE = os.path.join(KEYS_DIR, "omdbapikey.txt")
GROQ_KEY_FILE = os.path.join(KEYS_DIR, "groqapikey.txt")
SUBDL_KEY_FILE = os.path.join(KEYS_DIR, "subdlapikey.txt")


def ensure_config_dirs():
    """Kreira sve potrebne foldere ako ne postoje."""
    dirs = [
        CONFIG_DIR,
        KEYS_DIR,
        SUBTITLES_DIR,
        POSTERS_CACHE_DIR,
        EPG_CACHE_DIR,
    ]
    for d in dirs:
        if not os.path.exists(d):
            try:
                os.makedirs(d)
                print(f"[CiefpSfiles] Created directory: {d}")
            except Exception as e:
                print(f"[CiefpSfiles] Failed to create {d}: {e}")


def get_plugin_dir():
    """Vraća putanju do foldera plugina (za ikonice, skinove)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def migrate_old_files():
    """Prebacuje stare fajlove iz foldera plugina u /etc/enigma2/CiefpSfiles/"""
    plugin_dir = get_plugin_dir()
    
    # Mapa: stara putanja (u plugin folderu) -> nova putanja (u /etc/enigma2/)
    migrations = {
        os.path.join(plugin_dir, "tmdbapikey.txt"): TMDB_KEY_FILE,
        os.path.join(plugin_dir, "omdbapikey.txt"): OMDB_KEY_FILE,
        os.path.join(plugin_dir, "groqapikey.txt"): GROQ_KEY_FILE,
        os.path.join(plugin_dir, "subdlapikey.txt"): SUBDL_KEY_FILE,
        os.path.join(plugin_dir, "playlist.txt"): PLAYLIST_FILE,
        os.path.join(plugin_dir, "portals_cache.json"): CACHE_FILE,
    }
    
    for old_path, new_path in migrations.items():
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                import shutil
                shutil.copy2(old_path, new_path)
                print(f"[CiefpSfiles] Migrated: {old_path} -> {new_path}")
            except Exception as e:
                print(f"[CiefpSfiles] Migration failed for {old_path}: {e}")
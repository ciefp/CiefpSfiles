# -*- coding: utf-8 -*-
import os
import json
import time

from .paths import CONFIG_DIR

def _get_history_file():
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR)
        except Exception:
            pass
    return os.path.join(CONFIG_DIR, "recently_viewed.json")

def _load_history():
    path = _get_history_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_history(data):
    path = _get_history_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("[RecentlyViewed] Save error:", e)


def add_viewed_item(portal_host, item_type, item_id, item_name, extra_data=None):
    if not portal_host or not item_id:
        return
    data = _load_history()
    if portal_host not in data:
        data[portal_host] = {}
    if item_type not in data[portal_host]:
        data[portal_host][item_type] = []

    # Pronađi postojeći unos (ako postoji) da sačuvamo watched_episodes
    existing_entry = None
    for x in data[portal_host][item_type]:
        if str(x.get("id")) == str(item_id):
            existing_entry = x
            break

    # Ukloni postojeći unos
    data[portal_host][item_type] = [
        x for x in data[portal_host][item_type] if str(x.get("id")) != str(item_id)
    ]

    # Napravi novi unos
    entry = {
        "id": str(item_id),
        "name": item_name,
        "timestamp": int(time.time())
    }
    if extra_data:
        entry.update(extra_data)

    # Ako je postojao stari unos sa watched_episodes, sačuvaj ih
    if existing_entry and "watched_episodes" in existing_entry:
        entry["watched_episodes"] = existing_entry["watched_episodes"]

    data[portal_host][item_type].insert(0, entry)
    data[portal_host][item_type] = data[portal_host][item_type][:50]
    _save_history(data)


def get_viewed_items(portal_host, item_type):
    data = _load_history()
    return data.get(portal_host, {}).get(item_type, [])

def get_watched_episodes(portal_host, series_id):
    """Vraća listu gledanih epizoda za datu seriju u formatu 'sezona_epizoda'."""
    data = _load_history()
    series_list = data.get(portal_host, {}).get("series", [])
    for item in series_list:
        if str(item.get("id")) == str(series_id):
            return item.get("watched_episodes", [])
    return []


def mark_episode_watched(portal_host, series_id, season, episode):
    """Označava epizodu kao gledanu."""
    data = _load_history()
    if portal_host not in data:
        data[portal_host] = {}
    if "series" not in data[portal_host]:
        data[portal_host]["series"] = []

    found = False
    for item in data[portal_host]["series"]:
        if str(item.get("id")) == str(series_id):
            found = True
            if "watched_episodes" not in item:
                item["watched_episodes"] = []
            key = f"{season}_{episode}"
            if key not in item["watched_episodes"]:
                item["watched_episodes"].append(key)
            break

    if not found:
        data[portal_host]["series"].append({
            "id": str(series_id),
            "name": "",
            "watched_episodes": [f"{season}_{episode}"]
        })

    _save_history(data)
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
    data[portal_host][item_type] = [
        x for x in data[portal_host][item_type] if str(x.get("id")) != str(item_id)
    ]
    entry = {
        "id": str(item_id),
        "name": item_name,
        "timestamp": int(time.time())
    }
    if extra_data:
        entry.update(extra_data)
    data[portal_host][item_type].insert(0, entry)
    data[portal_host][item_type] = data[portal_host][item_type][:50]
    _save_history(data)

def get_viewed_items(portal_host, item_type):
    data = _load_history()
    return data.get(portal_host, {}).get(item_type, [])
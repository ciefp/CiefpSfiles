# -*- coding: utf-8 -*-
import os
import json
import time
from .paths import CACHE_FILE

def _get_cache_file():
    return CACHE_FILE

def load_cache():
    path = _get_cache_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(portal_id, is_online, msg, user_info):
    path = _get_cache_file()
    cache = load_cache()
    
    exp = user_info.get("exp_date")
    exp_str = "-"
    if exp:
        try:
            exp_str = time.strftime("%d.%m.%Y", time.localtime(int(exp)))
        except Exception:
            exp_str = str(exp)

    cache[str(portal_id)] = {
        "online": is_online,
        "msg": msg,
        "checked_at": time.strftime("%d.%m.%Y %H:%M"),
        "expires": exp_str,
        "max_conn": user_info.get("max_connections", "-"),
        "active_conn": user_info.get("active_cons", "-"),
        "status": user_info.get("status", "-")
    }
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        print(f"[CiefpSfiles] Cache save error: {e}")
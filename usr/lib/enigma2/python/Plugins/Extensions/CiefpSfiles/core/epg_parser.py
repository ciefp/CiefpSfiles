# -*- coding: utf-8 -*-
import os
import gzip
import urllib.request
import ssl
import threading
from datetime import datetime
import xml.etree.ElementTree as ET

_EPG_CACHE = {} # {"channel_name": [{"start": ts, "stop": ts, "title": "..."}]}

def _get_cache_dir():
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(plugin_dir, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir

def _parse_time(time_str):
    """Pretvara '20261020193000 +0000' u Unix timestamp."""
    try:
        # Uzimamo samo prvih 14 karaktera (YYYYMMDDHHMMSS)
        dt = datetime.strptime(time_str[:14], "%Y%m%d%H%M%S")
        return int(dt.timestamp())
    except Exception:
        return 0

def download_epg_async(epg_url, callback=None):
    """Skida XMLTV fajl sa Xtream servera u pozadini."""
    def worker():
        cache_file = os.path.join(_get_cache_dir(), "epg.xml")
        
        # Ako je fajl star manje od 12 sati, ne skidaj ponovo
        if os.path.exists(cache_file):
            if (datetime.now().timestamp() - os.path.getmtime(cache_file)) < 43200:
                if callback: callback(True, "Cached")
                return

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(epg_url, headers={'User-Agent': 'CiefpSFiles'})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
                
            # Provera da li je gzip
            if data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)
                
            with open(cache_file, 'wb') as f:
                f.write(data)
                
            if callback: callback(True, "Downloaded")
        except Exception as e:
            print(f"[CiefpSFiles] EPG Download Error: {e}")
            if callback: callback(False, str(e))

    threading.Thread(target=worker, daemon=True).start()

def load_epg_from_cache():
    """Učitava XMLTV iz keša i puni globalni _EPG_CACHE."""
    global _EPG_CACHE
    cache_file = os.path.join(_get_cache_dir(), "epg.xml")
    
    if not os.path.exists(cache_file):
        return False

    try:
        tree = ET.parse(cache_file)
        root = tree.getroot()
        
        # Prvo pokupimo mapiranje ID-ja kanala na ime
        channel_map = {}
        for channel in root.findall('channel'):
            ch_id = channel.get('id')
            display_name = channel.find('display-name')
            if display_name is not None:
                channel_map[ch_id] = display_name.text

        # Sada punimo programe
        _EPG_CACHE = {}
        for programme in root.findall('programme'):
            ch_id = programme.get('channel')
            ch_name = channel_map.get(ch_id, ch_id)
            
            start = _parse_time(programme.get('start', ''))
            stop = _parse_time(programme.get('stop', ''))
            title = programme.find('title')
            
            if start and title is not None:
                if ch_name not in _EPG_CACHE:
                    _EPG_CACHE[ch_name] = []
                _EPG_CACHE[ch_name].append({
                    "start": start,
                    "stop": stop,
                    "title": title.text
                })
        
        # Sortiramo po vremenu početka
        for ch in _EPG_CACHE:
            _EPG_CACHE[ch].sort(key=lambda x: x["start"])
            
        print(f"[CiefpSFiles] EPG loaded for {len(_EPG_CACHE)} channels.")
        return True
    except Exception as e:
        print(f"[CiefpSFiles] EPG Parse Error: {e}")
        return False

def get_current_epg(channel_name):
    """Vraća trenutnu i sledeću emisiju za zadati kanal."""
    if not _EPG_CACHE:
        return None
        
    # Ponekad se imena kanala u EPG-u razlikuju od onih u listi (npr. "HBO2 HD" vs "HBO2")
    # Zato tražimo najbliže poklapanje
    best_match = None
    for epg_ch in _EPG_CACHE.keys():
        if channel_name.lower() in epg_ch.lower() or epg_ch.lower() in channel_name.lower():
            best_match = epg_ch
            break
            
    if not best_match:
        return None

    now = int(datetime.now().timestamp())
    programs = _EPG_CACHE[best_match]
    
    current = None
    next_prog = None
    
    for i, prog in enumerate(programs):
        if prog["start"] <= now < prog["stop"]:
            current = prog
            if i + 1 < len(programs):
                next_prog = programs[i + 1]
            break
            
    return {"current": current, "next": next_prog}
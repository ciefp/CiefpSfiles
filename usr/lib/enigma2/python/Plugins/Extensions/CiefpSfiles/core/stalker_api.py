# -*- coding: utf-8 -*-
"""Ministra/Stalker portal client with an Xtream-shaped UI compatibility layer.

The UI in this plugin predates the Stalker backend.  This module deliberately
normalises portal responses to the small set of fields used by those screens,
allowing the original skins and navigation to remain unchanged.
"""
from __future__ import absolute_import, print_function

import json
import hashlib
import re
import ssl
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPSHandler
from urllib.error import HTTPError, URLError

DEFAULT_TIMEOUT = 20
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def _clean_mac(value):
    raw = re.sub(r"[^0-9A-Fa-f]", "", value or "")
    if len(raw) != 12:
        raise ValueError("MAC address must contain 12 hexadecimal characters")
    return ":".join(raw[i:i + 2] for i in range(0, 12, 2)).upper()


def _portal_endpoint(host):
    host = (host or "").strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    if host.endswith("/c"):
        host = host[:-2].rstrip("/")
    if host.endswith(("/server/load.php", "/portal.php", "/load.php")):
        return host
    # Most modern Ministra installs use portal.php.  server/load.php is retried
    # automatically by _request for older MAG portals.
    return host + "/portal.php"


class StalkerAPI(object):
    def __init__(self, host, mac, password="", timeout=DEFAULT_TIMEOUT):
        self.host = (host or "").rstrip("/")
        if self.host.endswith("/c"):
            self.host = self.host[:-2].rstrip("/")
        self.mac = _clean_mac(mac)
        self.password = password or ""  # optional device/portal password
        self.timeout = timeout
        self.portal = _portal_endpoint(host)
        self.token = ""
        self.random = ""
        self._profile = {}
        self._commands = {"itv": {}, "vod": {}, "series": {}}

    @property
    def username(self):  # retained for old skin helpers
        return self.mac

    @property
    def user_info(self):
        return self._profile

    @property
    def server_info(self):
        return {"url": self.host, "portal": self.portal}

    def _headers(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 MAG200 stbapp",
            "X-User-Agent": "Model: MAG254; Link: Ethernet",
            "Accept": "application/json, */*",
            "Cookie": "mac={}; stb_lang=en; timezone=Europe%2FLondon".format(self.mac.replace(":", "%3A")),
            "Referer": self.host + "/c/",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        return headers

    @staticmethod
    def _unwrap(payload):
        if isinstance(payload, dict) and "js" in payload:
            return payload.get("js")
        return payload

    def _request_once(self, endpoint, params):
        query = dict(params)
        query.setdefault("JsHttpRequest", "1-xml")
        req = Request(endpoint + "?" + urlencode(query), headers=self._headers())
        opener = build_opener(HTTPSHandler(context=_SSL))
        with opener.open(req, timeout=self.timeout) as response:
            text = response.read().decode("utf-8", "ignore").lstrip("\ufeff").strip()
            return json.loads(text) if text else None

    def _request(self, content_type, action, _reauth=True, **params):
        params.update({"type": content_type, "action": action})
        endpoints = [self.portal]
        base = self.host.rstrip("/")
        for suffix in ("/server/load.php", "/portal.php", "/load.php"):
            if base.endswith(suffix):
                base = base[:-len(suffix)].rstrip("/")
                break
        for suffix in ("/portal.php", "/server/load.php"):
            candidate = base + suffix
            if candidate not in endpoints:
                endpoints.append(candidate)
        last_error = None
        for endpoint in endpoints:
            try:
                payload = self._request_once(endpoint, params)
                self.portal = endpoint
                data = self._unwrap(payload)
                error_text = ""
                if isinstance(data, dict):
                    error_text = str(data.get("error") or data.get("message") or "").lower()
                if data is False or any(word in error_text for word in ("auth", "token", "access denied")):
                    last_error = RuntimeError(error_text or "portal authorization failed")
                    continue
                return data
            except (HTTPError, URLError, ValueError, TypeError, json.JSONDecodeError) as error:
                last_error = error
        # Tokens commonly expire while a menu remains open. Re-handshake once
        # and replay the failed request rather than forcing the user to reconnect.
        if _reauth and action != "handshake" and self.token:
            self.token = ""
            try:
                self._ensure_auth()
                return self._request(content_type, action, _reauth=False, **{k: v for k, v in params.items()
                                                                            if k not in ("type", "action")})
            except Exception as error:
                last_error = error
        raise RuntimeError("Portal request failed: {}".format(last_error or "empty response"))

    def _ensure_auth(self):
        if self.token:
            return
        data = self._request("stb", "handshake", token="", prehash="") or {}
        if not isinstance(data, dict) or not data.get("token"):
            raise RuntimeError("Stalker handshake did not return a token")
        self.token = str(data.get("token"))
        self.random = str(data.get("random") or "")

    def get_player_api(self):
        try:
            self._ensure_auth()
            serial = hashlib.md5(self.mac.encode("ascii")).hexdigest().upper()[:13]
            device_id = hashlib.sha256(self.mac.encode("ascii")).hexdigest().upper()
            signature = hashlib.sha256((device_id + device_id).encode("ascii")).hexdigest().upper()
            metrics = json.dumps({"mac": self.mac, "sn": serial, "model": "MAG254",
                                  "type": "STB", "uid": "", "random": self.random}, separators=(",", ":"))
            profile = self._request(
                "stb", "get_profile", hd="1", ver="ImageDescription: 0.2.18-r23-254; PORTAL version: 5.3.0",
                num_banks="2", sn=serial, stb_type="MAG254", client_type="STB", image_version="218",
                video_out="hdmi", device_id=device_id, device_id2=device_id, signature=signature,
                auth_second_step="1", hw_version="2.6-IB-00", metrics=metrics,
                hw_version_2=hashlib.sha1(self.mac.encode("ascii")).hexdigest(),
                timestamp=str(int(time.time())), api_signature="262",
                prehash=hashlib.sha1((serial + self.mac).encode("ascii")).hexdigest(),
                password=self.password,
            ) or {}
            if not isinstance(profile, dict):
                profile = {}
            self._profile = profile
            account = {}
            try:
                account = self._request("account_info", "get_main_info") or {}
            except Exception:
                pass
            expiry = account.get("phone") or account.get("end_date") or account.get("expire_billing_date") or "-"
            user_info = {
                "auth": 1, "status": "Active", "mac": self.mac,
                "exp_date": expiry, "max_connections": 1, "active_cons": 0,
                "name": profile.get("name") or profile.get("login") or self.mac,
            }
            self._profile.update(user_info)
            return True, {"user_info": user_info, "server_info": self.server_info}, None
        except Exception as error:
            self.token = ""
            return False, None, str(error)

    def is_active(self):
        return bool(self.token)

    def expires_str(self):
        return str(self._profile.get("exp_date") or "-")

    def max_connections(self):
        return 1

    def active_connections(self):
        return 0

    def _safe(self, callback, empty):
        try:
            self._ensure_auth()
            return True, callback(), None
        except Exception as error:
            return False, empty, str(error)

    def _categories(self, content_type):
        action = "get_genres" if content_type == "itv" else "get_categories"
        data = self._request(content_type, action) or []
        if isinstance(data, dict):
            data = data.get("data") or []
        return [{"category_id": str(x.get("id", "*")),
                 "category_name": x.get("title") or x.get("name") or "Unknown"}
                for x in data if isinstance(x, dict)]

    @staticmethod
    def _data_rows(raw):
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get("data") or raw.get("items") or []
        return []

    def _paged(self, content_type, action, **params):
        """Download every page while tolerating the common portal counters."""
        output, seen = [], set()
        page = 1
        while page <= 500:
            query = dict(params)
            query["p"] = str(page)
            raw = self._request(content_type, action, **query) or {}
            rows = self._data_rows(raw)
            if not rows:
                break
            added = 0
            for row in rows:
                marker = str(row.get("id") or row.get("ch_id") or row.get("name") or row) if isinstance(row, dict) else str(row)
                if marker not in seen:
                    seen.add(marker)
                    output.append(row)
                    added += 1
            if not added:
                break
            total = 0
            per_page = len(rows)
            if isinstance(raw, dict):
                try:
                    total = int(raw.get("total_items") or raw.get("total") or 0)
                    per_page = int(raw.get("max_page_items") or raw.get("per_page") or per_page)
                except (TypeError, ValueError):
                    total = 0
            if total and len(output) >= total:
                break
            if not total and len(rows) < max(1, per_page):
                break
            page += 1
        return output

    def get_live_categories(self):
        return self._safe(lambda: self._categories("itv"), [])

    def get_vod_categories(self):
        return self._safe(lambda: self._categories("vod"), [])

    def get_series_categories(self):
        return self._safe(lambda: self._categories("series"), [])

    def _listing(self, content_type, category=None):
        if content_type == "itv":
            raw = self._request("itv", "get_all_channels") or []
            raw = self._data_rows(raw)
        else:
            extra = {"category": category or "*", "sortby": "name"}
            if content_type == "series":
                extra.update({"movie_id": "0", "season_id": "0", "episode_id": "0"})
            raw = self._paged(content_type, "get_ordered_list", **extra)
        result = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            group = str(item.get("tv_genre_id") or item.get("category_id") or item.get("category") or "")
            if content_type == "itv" and category and str(category) not in ("*", "0") and group != str(category):
                continue
            media_id = str(item.get("id") or item.get("ch_id") or item.get("movie_id") or "")
            command = item.get("cmd") or item.get("command") or ""
            self._commands[content_type][media_id] = {
                "cmd": command, "item": item,
                "protocol": item.get("protocol", ""), "forced_storage": item.get("forced_storage", ""),
                "disable_ad": item.get("disable_ad", "0"), "download": item.get("download", "0"),
                "use_http_tmp_link": item.get("use_http_tmp_link", "0"),
                "use_load_balancing": item.get("use_load_balancing", "0"),
            }
            common = {
                "name": item.get("name") or item.get("title") or "Untitled",
                "stream_icon": item.get("logo") or item.get("screenshot_uri") or item.get("cover") or "",
                "cover": item.get("cover") or item.get("screenshot_uri") or "",
                "category_id": group, "rating": item.get("rating_imdb") or item.get("rating") or "",
                "plot": item.get("description") or item.get("plot") or "",
                "added": item.get("added") or item.get("year") or "",
                "container_extension": "mp4",
            }
            if content_type == "series":
                common["series_id"] = media_id
            else:
                common["stream_id"] = media_id
            result.append(common)
        return result

    def get_live_streams(self, category_id=None):
        return self._safe(lambda: self._listing("itv", category_id), [])

    def get_vod_streams(self, category_id=None):
        return self._safe(lambda: self._listing("vod", category_id), [])

    def get_series(self, category_id=None):
        return self._safe(lambda: self._listing("series", category_id), [])

    def _create_link(self, content_type, media_id, series=""):
        record = self._commands.get(content_type, {}).get(str(media_id), {})
        command = record.get("cmd") or str(media_id)
        if str(command).startswith("/media/") and not str(command).startswith("/media/file_"):
            # Some middleware returns a generic media command in list results.
            # Resolve it to the storage file id expected by create_link.
            try:
                lookup_type = "series" if content_type == "series" else "vod"
                lookup_id = record.get("movie_id") or media_id
                detail = self._request(lookup_type, "get_ordered_list", movie_id=str(lookup_id),
                                       season_id="0", episode_id="0", category="1", sortby="", p="1") or {}
                rows = self._data_rows(detail)
                resolved_id = rows[0].get("id") if rows and isinstance(rows[0], dict) else ""
                if resolved_id:
                    extension = ".mp4"
                    match = re.search(r"(\.[A-Za-z0-9]{2,5})$", str(command))
                    if match:
                        extension = match.group(1)
                    command = "/media/file_{}{}".format(resolved_id, extension)
            except Exception:
                pass
        clean_command = re.sub(r"^(ffmpeg|auto)\s+", "", str(command)).strip()
        force_resolve = str(record.get("protocol", "")).lower() == "custom"
        force_resolve = force_resolve or str(record.get("use_http_tmp_link", "0")).lower() in ("1", "true", "yes")
        force_resolve = force_resolve or str(record.get("use_load_balancing", "0")).lower() in ("1", "true", "yes")
        if "://" in clean_command and not force_resolve:
            return clean_command

        request_type = "vod" if content_type == "series" else content_type
        data = self._request(request_type, "create_link", cmd=command, series=series or record.get("episode_id", ""),
                             forced_storage=record.get("forced_storage", ""),
                             disable_ad=record.get("disable_ad", "0"), download=record.get("download", "0"),
                             force_ch_link_check="0") or {}
        if isinstance(data, list):
            candidates = [x for x in data if isinstance(x, dict) and x.get("type") != "ad" and x.get("cmd")]
            data = candidates[0] if candidates else (data[0] if data else {})
        link = data.get("cmd") or data.get("url") or "" if isinstance(data, dict) else ""
        link = re.sub(r"^(ffmpeg|auto)\s+", "", str(link)).strip()
        if not link:
            raise RuntimeError("Portal did not return a playable link")
        return link

    def build_live_url(self, stream_id, ext="ts"):
        return self._create_link("itv", stream_id)

    def build_live_hls_url(self, stream_id):
        return self._create_link("itv", stream_id)

    def build_movie_url(self, stream_id, ext="mp4"):
        return self._create_link("vod", stream_id)

    def build_series_url(self, episode_id, ext="mp4"):
        record = self._commands["series"].get(str(episode_id), {})
        return self._create_link("series", episode_id, str(record.get("episode_id") or episode_id))

    def get_vod_info(self, vod_id):
        def load():
            item = self._commands["vod"].get(str(vod_id), {}).get("item", {})
            if not item:
                raw = self._request("vod", "get_ordered_list", movie_id=str(vod_id), category="*", p="1") or {}
                rows = raw.get("data", []) if isinstance(raw, dict) else raw
                item = rows[0] if rows else {}
                if item:
                    self._commands["vod"][str(vod_id)] = {"cmd": item.get("cmd") or "", "item": item}
            return {"info": item, "movie_data": item}
        return self._safe(load, None)

    def get_series_info(self, series_id):
        def load():
            rows = self._paged("series", "get_ordered_list", movie_id=str(series_id), season_id="0",
                               episode_id="0", category="*", sortby="")
            episodes = {}
            for row in rows or []:
                season_id = str(row.get("id") or "")
                season = str(row.get("season") or (season_id.split(":", 1)[1] if ":" in season_id else 1))
                episode_numbers = row.get("series")
                if not isinstance(episode_numbers, list):
                    episode_numbers = [row.get("episode") or row.get("episode_num") or row.get("episode_id") or 1]
                for episode_number in episode_numbers:
                    eid = "{}:{}:{}".format(series_id, season, episode_number)
                    self._commands["series"][eid] = {
                        "cmd": row.get("cmd") or "", "item": row, "episode_id": str(episode_number),
                        "movie_id": str(series_id),
                        "protocol": row.get("protocol", ""), "forced_storage": row.get("forced_storage", ""),
                        "disable_ad": row.get("disable_ad", "0"), "download": row.get("download", "0"),
                    }
                    ep = dict(row)
                    ep.update({"id": eid, "episode_num": episode_number,
                               "title": "Episode {}".format(episode_number), "season": season,
                               "container_extension": "mp4"})
                    episodes.setdefault(season, []).append(ep)
            return {"info": self._commands["series"].get(str(series_id), {}).get("item", {}), "episodes": episodes}
        return self._safe(load, None)

    def get_short_epg(self, stream_id, limit=10):
        def load():
            raw = self._request("itv", "get_short_epg", ch_id=str(stream_id), size=str(limit)) or {}
            rows = raw.get("data", []) if isinstance(raw, dict) else raw
            listings = []
            for event in rows or []:
                listings.append({"title": event.get("name") or event.get("title") or "",
                                 "description": event.get("descr") or event.get("description") or "",
                                 "start": event.get("start_timestamp") or event.get("start") or 0,
                                 "end": event.get("stop_timestamp") or event.get("end") or 0,
                                 "start_timestamp": event.get("start_timestamp") or event.get("start") or 0,
                                 "stop_timestamp": event.get("stop_timestamp") or event.get("end") or 0})
            return {"epg_listings": listings}
        return self._safe(load, None)



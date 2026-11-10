# -*- coding: utf-8 -*-
"""Parser for CiefpSfiles portal/MAC playlists."""
from __future__ import absolute_import, print_function

import os
import re
from urllib.parse import urlparse

from .paths import PLAYLIST_FILE

_MAC = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}$")


def normalize_mac(value):
    raw = re.sub(r"[^0-9A-Fa-f]", "", value or "")
    if len(raw) != 12:
        return ""
    return ":".join(raw[i:i + 2] for i in range(0, 12, 2)).upper()


def _name(portal, index):
    if portal.get("alias"):
        return portal["alias"]
    try:
        domain = urlparse(portal.get("host", "")).netloc
    except Exception:
        domain = portal.get("host", "")
    return "{} ({})".format(domain or "Portal {}".format(index + 1), portal.get("mac", ""))


def parse_playlist_file(path=None):
    path = path or PLAYLIST_FILE
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as source:
            lines = source.readlines()
    except Exception as error:
        print("[CiefpSfiles] cannot read portals: {}".format(error))
        return []

    portals, current_host, pending = [], "", {}

    def add(host, mac, alias="", password=""):
        mac = normalize_mac(mac)
        if not host or not mac:
            return
        portal = {"host": host.rstrip("/"), "mac": mac, "alias": alias.strip(), "password": password.strip()}
        portal["username"] = mac  # compatibility for older UI code
        portal["id"] = len(portals)
        portal["name"] = _name(portal, portal["id"])
        portals.append(portal)

    def flush():
        nonlocal pending
        if pending:
            add(pending.get("host") or current_host, pending.get("mac"), pending.get("alias", ""), pending.get("password", ""))
            pending = {}

    for raw in lines + ["\n"]:
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            continue
        if line.lower().startswith(("http://", "https://")):
            flush()
            current_host = line.rstrip("/")
            continue
        # EStalker format: MAC # optional alias
        value, _, comment = line.partition("#")
        if _MAC.match(value.strip()):
            flush()
            add(current_host, value.strip(), comment.strip())
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if key in ("host", "portal", "url"):
            flush()
            current_host = value.rstrip("/")
            pending["host"] = current_host
        elif key in ("mac", "mac_address"):
            if pending.get("mac"):
                flush()
            pending["host"] = pending.get("host") or current_host
            pending["mac"] = value
        elif key in ("alias", "name"):
            pending["alias"] = value
        elif key in ("password", "device_password"):
            pending["password"] = value

    print("[CiefpSfiles] parsed {} portal identities from {}".format(len(portals), path))
    return portals


def save_portal_to_file(path, portal):
    host, mac = portal.get("host", "").rstrip("/"), normalize_mac(portal.get("mac") or portal.get("username"))
    if not host or not mac:
        return False
    try:
        with open(path, "a", encoding="utf-8") as output:
            output.write("\nHost:{}\nMac:{}\n".format(host, mac))
            if portal.get("alias"):
                output.write("Alias:{}\n".format(portal["alias"]))
            if portal.get("password"):
                output.write("Device_Password:{}\n".format(portal["password"]))
        return True
    except Exception as error:
        print("[CiefpSfiles] save error: {}".format(error))
        return False


def remove_portal_from_file(path, portal):
    if not path or not os.path.exists(path):
        return False
    target_host = portal.get("host", "").rstrip("/")
    target_mac = normalize_mac(portal.get("mac") or portal.get("username"))
    parsed = parse_playlist_file(path)
    remaining = [x for x in parsed if not (x.get("host") == target_host and x.get("mac") == target_mac)]
    try:
        with open(path, "w", encoding="utf-8") as output:
            for item in remaining:
                output.write("Host:{}\nMac:{}\n".format(item["host"], item["mac"]))
                if item.get("alias"):
                    output.write("Alias:{}\n".format(item["alias"]))
                if item.get("password"):
                    output.write("Device_Password:{}\n".format(item["password"]))
                output.write("\n")
        return True
    except Exception as error:
        print("[CiefpSfiles] remove error: {}".format(error))
        return False

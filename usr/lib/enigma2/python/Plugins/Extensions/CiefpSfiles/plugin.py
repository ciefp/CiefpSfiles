# -*- coding: utf-8 -*-
#
# CiefpStalkerFiles - Stalker/Ministra IPTV plugin for Enigma2 (Python 3)
# Stalker/Ministra backend with the original CiefpXfiles screen layouts.
#
from __future__ import absolute_import, print_function
from .core.paths import ensure_config_dirs, migrate_old_files, CONFIG_DIR

# Na startu plugina, obezbedi foldere i migriraj stare fajlove
ensure_config_dirs()
migrate_old_files()

import os

from Plugins.Plugin import PluginDescriptor

PLUGIN_NAME = "CiefpSfiles"
PLUGIN_DESC = "Stalker/Ministra IPTV plugin with TMDB/OMDb enrichment"
PLUGIN_VERSION = "2.0.0"
PLUGIN_DIR = os.path.dirname(__file__) if '__file__' in globals() else \
    "/usr/lib/enigma2/python/Plugins/Extensions/CiefpSfiles"

PLUGIN_ICON = os.path.join(PLUGIN_DIR, "icons", "icon.png")
PLUGIN_LOGO = os.path.join(PLUGIN_DIR, "icons", "plugin_logo.png")
PLACEHOLDER = os.path.join(PLUGIN_DIR, "icons", "placeholder.png")
PLAYLIST_FILE = os.path.join(PLUGIN_DIR, "playlist.txt")

def main(session, **kwargs):
    from .ui.portal_screen import PortalScreen
    session.open(PortalScreen)   # <-- BEZ session!

def Plugins(**kwargs):
    icon = PLUGIN_ICON if os.path.exists(PLUGIN_ICON) else None
    return [
        PluginDescriptor(
            name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
            description=PLUGIN_DESC,
            icon=icon,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        ),
        PluginDescriptor(
            name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
            where=PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU,
            fnc=main
        ),
    ]

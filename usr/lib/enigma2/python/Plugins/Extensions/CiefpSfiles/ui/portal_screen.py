# -*- coding: utf-8 -*-
#
# portal_screen.py - Ekran 1: lista portala iz playlist.txt
#
from __future__ import absolute_import, print_function

import os
import threading

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER

from ..core.playlist_parser import (
    parse_playlist_file,
    remove_portal_from_file,
)
from ..core.stalker_api import StalkerAPI
from ..core.portal_cache import load_cache, save_cache
from .settings_screen import SettingsScreen

def _load_pixmap_safe(path):
    if path and os.path.exists(path):
        try:
            return LoadPixmap(path)
        except Exception:
            return None
    return None
from enigma import eConsoleAppContainer
from Screens.MessageBox import MessageBox
import os

PLUGIN_VERSION = "2.0.0"
VERSION_URL = "https://raw.githubusercontent.com/ciefp/CiefpSfiles/main/version.txt"
UPDATE_COMMAND = "wget -q --no-check-certificate https://raw.githubusercontent.com/ciefp/CiefpSfiles/main/installer.sh -O - | /bin/sh"

class PortalScreen(Screen):
    skin = """
        <screen name="CiefpSfilesPortal" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="select_label" position="40,110" size="600,50" font="Bold;32"
                    halign="left" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="portal_list" position="40,170" size="700,750"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;28" backgroundColor="#011a2e"/>

            <widget name="info" position="780,170" size="480,780"
                    font="Regular;26" valign="top" backgroundColor="#011a2e"
                    foregroundColor="#FFFFFF"/>

            <widget name="logo" position="1300,170" size="560,780"
                    alphatest="blend" zPosition="2"/>

            <widget name="status" position="600,950" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
            <widget name="version_status" position="1280,1010" size="820,40" font="Regular;22"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" halign="left"/>
            <widget name="page_info" position="40,950" size="500,40"
                    font="Regular;22" halign="left" valign="center"
                    foregroundColor="#A0A0A0" backgroundColor="#011a2e" transparent="1"/>

            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000"
                    halign="center" valign="center"/>
            <ePixmap pixmap="buttons/green.png" position="240,1005" size="35,35" alphatest="blend"/>
            <eLabel text="CONNECT" position="290,1000" size="220,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000"
                    halign="center" valign="center"/>
            <ePixmap pixmap="buttons/yellow.png" position="530,1005" size="35,35" alphatest="blend"/>
            <eLabel text="CHECK" position="580,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#808000"
                    halign="center" valign="center"/>
            <ePixmap pixmap="buttons/blue.png" position="780,1005" size="35,35" alphatest="blend"/>
            <eLabel text="DELETE" position="830,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#000080"
                    halign="center" valign="center"/>
            <ePixmap pixmap="buttons/red.png" position="1020,1005" size="35,35" alphatest="blend"/>
            <eLabel text="SETTINGS" position="1070,1000" size="200,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#400080"
                    halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, playlist_path=None):
        Screen.__init__(self, session)
        self.session = session

        if playlist_path is not None and not isinstance(playlist_path, (str, bytes, os.PathLike)):
            playlist_path = None

        if playlist_path is None:
            from ..core.paths import PLAYLIST_FILE
            playlist_path = PLAYLIST_FILE
        self.playlist_path = playlist_path

        self["title"] = Label("..:: CiefpSfiles ::..")
        self["select_label"] = Label("SELECT PORTAL")
        
        # Koristimo MenuList sa podrškom za sličice
        self["portal_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["portal_list"].l.setItemHeight(50)
        self["portal_list"].l.setFont(0, gFont("Regular", 28))
        
        self["info"] = Label("")
        self["logo"] = Pixmap()
        self["status"] = Label("")
        self["version_status"] = Label("")
        self["page_info"] = Label("")

        self.portals = []
        self.check_results = {}
        self._check_in_progress = False

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.connect_selected,
                "yellow": self.check_selected,
                "blue": self.delete_selected,
                "ok": self.connect_selected,
                "up": self.on_up,
                "down": self.on_down,
                "left": self.on_up,
                "right": self.on_down,
                "menu": self.open_settings,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)
        # Inicijalizacija za update
        self.version_check_in_progress = False
        self.version_buffer = b''
        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.command_finished)
        self.container.dataAvail.append(self.version_data_avail)

        self.check_for_updates()
    # ---------- UPDATE PLUGIN ------------
    def check_for_updates(self):
        if self.version_check_in_progress:
            return
        self.version_check_in_progress = True
        self["version_status"].setText("Checking for updates...")
        try:
            self.container.execute(f"wget -q --timeout=10 -O - {VERSION_URL}")
        except Exception as e:
            self.version_check_in_progress = False
            self["version_status"].setText("Update check failed.")
            print("[CiefpSfiles] Update error:", e)

    def version_data_avail(self, data):
        self.version_buffer += data

    def command_finished(self, retval):
        if self.version_check_in_progress:
            self.version_check_closed(retval)
        else:
            self.update_completed(retval)

    def version_check_closed(self, retval):
        self.version_check_in_progress = False
        if retval == 0:
            try:
                remote_version = self.version_buffer.decode().strip()
                self.version_buffer = b''
                print(f"[CiefpSfiles] Local: {PLUGIN_VERSION}, Remote: {remote_version}")
                if remote_version != PLUGIN_VERSION:
                    self["version_status"].setText(f"New version available: v{remote_version}")
                    self.session.openWithCallback(
                        self.start_update,
                        MessageBox,
                        f"New version: v{remote_version}\nInstall now?",
                        MessageBox.TYPE_YESNO
                    )
                else:
                    self["version_status"].setText("The plugin is up to date.")
            except Exception as e:
                self["version_status"].setText("Version check failed.")
                print(f"[CiefpSfiles] Parse error: {e}")
        else:
            self["version_status"].setText("Update check failed.")

    def start_update(self, answer):
        if not answer:
            self["version_status"].setText("Update cancelled.")
            return
        self["version_status"].setText("Updating...")
        self.container.execute(UPDATE_COMMAND)

    def update_completed(self, retval):
        if retval == 0:
            self["version_status"].setText("Update OK! Restarting...")
            self.container.execute("sleep 2 && killall -9 enigma2")
        else:
            self["version_status"].setText("Update failed.")

    def on_start(self):
        self._load_logo()
        self.reload_portals()

    def _load_logo(self):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(plugin_dir, "icons", "plugin_logo.png")
        px = _load_pixmap_safe(logo_path)
        if px and self["logo"].instance:
            self["logo"].instance.setPixmap(px)

    def reload_portals(self):
        self.portals = parse_playlist_file(self.playlist_path)
        self.check_results = load_cache()
        self._refresh_list()
        if not self.portals:
            self["status"].setText(f"No portals found in {self.playlist_path}")
            self["info"].setText(
                "playlist.txt is empty or missing.\n\n"
                "Add portals in format:\n"
                "Host:http://server:port\n"
                "Mac:00:1A:79:XX:XX:XX\n"
                "Alias:Living room\n\n"
                "You may also place MAC lines below a portal URL."
            )

    def _refresh_list(self):
        items = []
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        icon_online = os.path.join(plugin_dir, "icons", "green.png")
        icon_offline = os.path.join(plugin_dir, "icons", "red.png")
        icon_unknown = os.path.join(plugin_dir, "icons", "yellow.png")

        for p in self.portals:
            name = p.get("name", "Portal")
            res = self.check_results.get(str(p.get("id")))
            
            if res is None:
                icon_path = icon_unknown if os.path.exists(icon_unknown) else icon_online
            elif res.get("online"):
                icon_path = icon_online
            else:
                icon_path = icon_offline

            text = f"{p.get('id', 0) + 1}. {name}"
            
            entry = [
                (name, res),
                MultiContentEntryPixmapAlphaTest(pos=(10, 15), size=(20, 20), png=loadPNG(icon_path)),
                MultiContentEntryText(
                    pos=(40, 0), size=(650, 50), font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=text
                )
            ]
            items.append(entry)

        self["portal_list"].setList(items)
        if items:
            self["portal_list"].moveToIndex(0)
            self._update_info(0)
        else:
            self["info"].setText("")
        total = len(self.portals)
        self["page_info"].setText(f"Page 1/1  Source:{total}/{total}")

    def _current_idx(self):
        try:
            return self["portal_list"].getSelectedIndex()
        except Exception:
            return 0

    def on_up(self):
        try:
            self["portal_list"].up()
            self._update_info(self._current_idx())
        except Exception:
            pass

    def on_down(self):
        try:
            self["portal_list"].down()
            self._update_info(self._current_idx())
        except Exception:
            pass

    def _update_info(self, idx):
        if not (0 <= idx < len(self.portals)):
            self["info"].setText("")
            return
        p = self.portals[idx]
        res = self.check_results.get(str(p.get("id")))

        lines = []
        if res is None:
            lines.append("PORTAL - NOT CHECKED")
        elif res.get("online"):
            lines.append("PORTAL - Online")
        else:
            lines.append(f"PORTAL - OFFLINE ({res.get('msg', 'error')})")

        lines.append("")
        lines.append(f"SERVER:      {p.get('host', '-')}")
        lines.append(f"MAC:         {p.get('mac', '-')}")
        lines.append(f"Alias:       {p.get('alias', '-')}")

        if res and res.get("online"):
            lines.append("")
            lines.append(f"Expires:           {res.get('expires', '-')}")
            lines.append(f"Last Check:        {res.get('checked_at', '-')}")
            lines.append(f"Maximum Connection:{res.get('max_conn', '-')}")
            lines.append(f"Active Connection: {res.get('active_conn', '-')}")
            lines.append(f"Status:            {res.get('status', '-')}")

        self["info"].setText("\n".join(lines))

    def connect_selected(self):
        idx = self._current_idx()
        if not (0 <= idx < len(self.portals)):
            return
        p = self.portals[idx]

        res = self.check_results.get(str(p.get("id")))
        if res and res.get("online"):
            if "data" in res and res["data"]:
                self._open_main_screen(p, res["data"])
                return
        
        self["status"].setText(f"Connecting to {p.get('name', 'portal')}...")
        self._set_busy(True)

        def worker():
            api = StalkerAPI(p["host"], p["mac"], p["password"])
            ok, data, err = api.get_player_api()
            if ok:
                import time
                save_cache(p["id"], True, "OK", data.get("user_info", {}))
                self.check_results[str(p["id"])] = {
                    "online": True,
                    "msg": "OK",
                    "data": data,
                }
                self._on_connect_ok(p, data)
            else:
                self.check_results[str(p["id"])] = {
                    "online": False,
                    "msg": err or "Offline",
                    "data": None,
                }
                self._on_connect_fail(p, err)

        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_ok(self, portal, data):
        from enigma import eTimer
        def _do():
            self._set_busy(False)
            self._refresh_list()
            self._update_info(self._current_idx())
            self["status"].setText(f"Connected: {portal.get('name', '')}")
            self._open_main_screen(portal, data)
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)

    def _on_connect_fail(self, portal, err):
        from enigma import eTimer
        def _do():
            self._set_busy(False)
            self._refresh_list()
            self._update_info(self._current_idx())
            self["info"].setText(
                f"PORTAL - OFFLINE\n\n"
                f"SERVER:   {portal.get('host', '-')}\n"
                f"Reason:   {err or 'unknown'}"
            )
            self["status"].setText(f"Connection failed: {err or 'error'}")
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)

    def _open_main_screen(self, portal, api_data):
        try:
            from .main_screen import MainScreen
            self.session.open(MainScreen, portal, api_data)
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Greška pri otvaranju glavnog ekrana:\n{e}",
                MessageBox.TYPE_ERROR, timeout=6
            )

    def check_selected(self):
        if self._check_in_progress:
            self["status"].setText("Check already in progress...")
            return
        if not self.portals:
            return

        self._check_in_progress = True
        self._set_busy(True)
        total = len(self.portals)
        self["status"].setText(f"Checking 0/{total} portals...")

        def worker():
            from enigma import eTimer
            for idx, p in enumerate(self.portals):
                api = StalkerAPI(p["host"], p["mac"], p["password"])
                ok, data, err = api.get_player_api()

                user_info = data.get("user_info", {}) if ok else {}
                save_cache(p["id"], ok, "OK" if ok else (err or "Offline"), user_info)

                self.check_results[str(p["id"])] = {
                    "online": ok,
                    "msg": "OK" if ok else (err or "Offline"),
                    "data": data if ok else None,
                }

                # Ažuriraj status i osveži listu na glavnom thread-u
                def _update_progress(current_idx, total_count, portal_id):
                    self["status"].setText(f"Checking {current_idx}/{total_count} portals...")
                    # Osveži listu da bi se odmah videla promena ikonice
                    self._refresh_list()

                t = eTimer()
                t.callback.append(lambda ci=idx + 1, tc=total, pid=p["id"]: _update_progress(ci, tc, pid))
                t.start(10, True)

            self._on_check_done()

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self):
        from enigma import eTimer

        def _show_final():
            self._check_in_progress = False
            self._set_busy(False)
            self._refresh_list()
            self._update_info(self._current_idx())
            online = sum(1 for r in self.check_results.values() if r.get("online"))
            total = len(self.check_results)
            self["status"].setText(f"Check completed: {online}/{total} online")

        # Prvo prikaži "Checking 30/30" na trenutak
        self["status"].setText(f"Checking {len(self.portals)}/{len(self.portals)} portals...")

        # Sačekaj 300ms pre nego što prikažeš finalnu poruku
        t = eTimer()
        t.callback.append(_show_final)
        t.start(300, True)


    def delete_selected(self):
        idx = self._current_idx()
        if not (0 <= idx < len(self.portals)):
            return
        p = self.portals[idx]
        msg = (f"Delete portal?\n\n"
               f"{p.get('name', '')}\n"
               f"{p.get('host', '')}\n\n"
               f"This will remove it from playlist.txt.")

        def confirm(result):
            if not result:
                return
            ok = remove_portal_from_file(self.playlist_path, p)
            if ok:
                self["status"].setText(f"Deleted: {p.get('name', '')}")
                self.reload_portals()
            else:
                self.session.open(
                    MessageBox,
                    "Failed to delete portal from playlist.txt",
                    MessageBox.TYPE_ERROR, timeout=5
                )

        self.session.openWithCallback(
            confirm, MessageBox, msg, MessageBox.TYPE_YESNO
        )

    def open_settings(self):
        self.session.open(SettingsScreen)

    def _set_busy(self, busy):
        self._busy = busy

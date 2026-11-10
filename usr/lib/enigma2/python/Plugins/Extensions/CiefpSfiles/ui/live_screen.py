# -*- coding: utf-8 -*-
#
# live_screen.py - Modern Live TV ekran sa Mini TV (Pig)
#
from __future__ import absolute_import, print_function

import os
import threading
import time

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Renderer.Pig import Pig
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.LoadPixmap import LoadPixmap
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from enigma import eTimer, eServiceReference, eEPGCache

from ..core.stalker_api import StalkerAPI
from ..core.config import config
from ..core.epg_parser import get_current_epg
from ..core.title_clean import clean_title

def _load_pixmap_safe(path):
    if path and os.path.exists(path):
        try:
            return LoadPixmap(path)
        except Exception:
            return None
    return None

def _get_icon_path(icon_name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", icon_name)

class LiveScreen(Screen):
    skin = """
        <screen name="CiefpStalkerFilesLive" position="0,0" size="1920,1080"
                flags="wfNoBorder" backgroundColor="#011a2e">

            <!-- NASLOV -->
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- LEVI PANEL: Lista kanala -->
            <widget name="left_list" position="40,110" size="650,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- DESNI PANEL: MINI TV (PiG) - Povećan -->
            <widget source="session.VideoPicture" render="Pig" position="750,110" size="650,366" backgroundColor="transparent" zPosition="10"/>
            <!-- Okvir oko PiG-a (PNG) -->
            <ePixmap position="745,105" size="658,374" zPosition="15" pixmap="%s" alphatest="blend" />
            <!-- INFO IKONICA (dinamička) -->
            <widget name="info_icon" position="1420,110" size="400,300" alphatest="blend" zPosition="15" transparent="1"/>

            <!-- SREDNJI/DESNI PANEL: EPG INFO ISPOD PiG-a -->
            
            <!-- NOW -->
            <widget name="channel_name" position="750,500" size="1150,40" font="Bold;30"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
                    
            <widget name="epg_now_time" position="750,570" size="200,30" font="Bold;28"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
                    
            <widget name="epg_now_title" position="1000,570" size="1000,30" font="Bold;28"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="epg_now_desc" position="750,620" size="1100,110" font="Regular;22"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- NEXT -->
            <widget name="epg_next_time" position="750,750" size="200,30" font="Bold;28"
                    foregroundColor="#FFFF00" backgroundColor="#011a2e" transparent="1"/>
                    
            <widget name="epg_next_title" position="1000,750" size="750,30" font="Bold;28"
                    foregroundColor="#FFFF00" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="epg_next_desc" position="750,800" size="1100,110" font="Regular;22"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- STATUS -->
            <widget name="status" position="720,950" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/green.png" position="240,1005" size="35,35" alphatest="blend"/>
            <eLabel text="LIVE" position="290,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/yellow.png" position="480,1005" size="35,35" alphatest="blend"/>
            <eLabel text="MOVIES" position="530,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#808000" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/blue.png" position="720,1005" size="35,35" alphatest="blend"/>
            <eLabel text="SERIES" position="770,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#000080" halign="center" valign="center"/>
            
            <ePixmap pixmap="buttons/red.png" position="960,1005" size="35,35" alphatest="blend"/>
            <eLabel text="MENU:SETTINGS" position="1010,1000" size="300,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#400080" halign="center" valign="center"/>
                                
            <ePixmap pixmap="buttons/green.png" position="1300,1005" size="35,35" alphatest="blend"/>
            <eLabel text="INFO:EPG" position="1350,1000" size="300,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#00802d" halign="center" valign="center"/>
        </screen>
    """ % _get_icon_path("frame_minitv.png")

    def __init__(self, session, portal, api_data):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])
        
        self.categories = []
        self.streams = []
        self.current_category = None
        
        # Tip plejera (sa fallback-om)
        try:
            self.player_type_live = config.plugins.ciefpsfiles.player_type_live.value
            if self.player_type_live == "4097":
                self.player_type_live = "5001"
        except Exception:
            self.player_type_live = "5001"
        
        # Logika za dupli klik
        self.last_ok_time = 0
        self.last_ok_index = -1
        self.preview_active = False
        self.preview_ref = None
        self._epg_timer = None
        
        # Widgets
        self["title"] = Label(f"..:: CiefpStalkerFiles Live - {portal.get('name', '')} ::..")
        self["info_icon"] = Pixmap()
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        
        self["channel_name"] = Label("")
        self["epg_now_title"] = Label("")
        self["epg_now_time"] = Label("")
        self["epg_now_desc"] = Label("")
        self["epg_next_title"] = Label("")
        self["epg_next_time"] = Label("")
        self["epg_next_desc"] = Label("")
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions", "InfoActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.show_live,
                "yellow": self.show_movies,
                "blue": self.show_series,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
                "menu": self.open_settings,
                "info": self.open_epg,   # INFO sada otvara EPG ekran
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def close(self, *args):
        if self.preview_active:
            try:
                self.session.nav.stopService()
            except Exception:
                pass
            self.preview_active = False
        Screen.close(self, *args)

    def on_start(self):
        self.show_live()

    def show_live(self):
        self["status"].setText("Loading Live categories...")
        ok, data, err = self.api.get_live_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def _render_categories(self):
        items = []
        items.append([
            ("BACK", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO HOME ]")
        ])
        
        icon_folder = _get_icon_path("icon_folder.png")
        for cat in self.categories:
            name = cat.get('category_name', 'Unknown')
            if os.path.exists(icon_folder):
                items.append([
                    (name, cat.get("category_id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_folder)),
                    MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
            else:
                items.append([
                    (name, cat.get("category_id")),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
                
        self["left_list"].setList(items)
        self["left_list"].moveToIndex(1)
        self["status"].setText(f"Loaded {len(self.categories)} categories.")

    def _load_streams_for_category(self):
        self["status"].setText("Loading streams...")
        ok, data, err = self.api.get_live_streams(self.current_category)
        if ok:
            self.streams = data
            items = []
            
            items.append([
                ("BACK", ""),
                MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="[ BACK TO CATEGORIES ]")
            ])

            icon_live = _get_icon_path("icon_live.png")
            for s in self.streams:
                name = clean_title(s.get("name", "Unknown"))
                epg_info = get_current_epg(name)
                epg_str = ""
                if epg_info and epg_info.get("current"):
                    epg_str = f" | {epg_info['current']['title']}"
                
                if os.path.exists(icon_live):
                    items.append([
                        (name, s.get("stream_id")),
                        MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_live)),
                        MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=f"{name}{epg_str}")
                    ])
                else:
                    items.append([
                        (name, s.get("stream_id")),
                        MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=f"{name}{epg_str}")
                    ])

            self["left_list"].setList(items)
            self["left_list"].moveToIndex(0)
            self["status"].setText(f"Loaded {len(self.streams)} items.")
            self._update_info()
            
            if self.streams and len(self.streams) > 0:
                self._play_preview(0)
        else:
            self["status"].setText(f"Error: {err}")

    def _update_info(self):
        idx = self["left_list"].getSelectedIndex()
        
        if self.current_category is None:
            self["channel_name"].setText("")
            self._clear_epg()
            return
            
        if idx == 0:
            self["channel_name"].setText("[ BACK TO CATEGORIES ]")
            self._clear_epg()
            return

        if 0 < idx <= len(self.streams):
            s = self.streams[idx - 1]
            name = clean_title(s.get("name", "Unknown"))
            stream_id = s.get("stream_id")

            self["channel_name"].setText(f"{name}")
            self._clear_epg()
            
            self["epg_now_title"].setText("Loading EPG...")
            
            if stream_id:
                threading.Thread(target=self._fetch_epg_async, args=(stream_id,), daemon=True).start()

    def _clear_epg(self):
        self["epg_now_title"].setText("")
        self["epg_now_time"].setText("")
        self["epg_now_desc"].setText("")
        self["epg_next_title"].setText("")
        self["epg_next_time"].setText("")
        self["epg_next_desc"].setText("")

    def _fetch_epg_async(self, stream_id):
        print(f"[CiefpStalkerFiles] EPG fetch started for stream_id: {stream_id}")

        # Prikaži ikonicu dok se ne utvrdi da li ima EPG-a
        try:
            icon_path = _get_icon_path("info.png")
            if os.path.exists(icon_path):
                px = _load_pixmap_safe(icon_path)
                if px and self["info_icon"].instance:
                    self["info_icon"].instance.setPixmap(px)
                    self["info_icon"].show()
        except Exception:
            pass

        try:
            import base64
            import time
            ok, data, error = self.api.get_short_epg(stream_id, limit=10)
            if not ok:
                raise RuntimeError(error or "EPG request failed")

            from enigma import eTimer
            def _update_ui():
                try:
                    if not data or "epg_listings" not in data:
                        self["epg_now_title"].setText("No EPG data")
                        # Sakrij ikonicu jer nema EPG-a
                        try:
                            self["info_icon"].hide()
                        except Exception:
                            pass
                        return

                    epg_listings = data.get("epg_listings", [])
                    if not epg_listings:
                        self["epg_now_title"].setText("No EPG data")
                        # Sakrij ikonicu
                        try:
                            self["info_icon"].hide()
                        except Exception:
                            pass
                        return

                    # Ako ima EPG, ikonica ostaje vidljiva (već je prikazana)

                    now = int(time.time())
                    current = None
                    next_prog = None

                    for listing in epg_listings:
                        try:
                            stop_ts = int(listing.get("stop_timestamp", 0))
                            if stop_ts >= now:
                                if current is None:
                                    current = listing
                                elif next_prog is None:
                                    next_prog = listing
                                    break
                        except Exception:
                            pass

                    if not current:
                        self["epg_now_title"].setText("No current program")
                        try:
                            self["info_icon"].hide()
                        except Exception:
                            pass
                        return

                    # NOW
                    try:
                        title = base64.b64decode(current.get("title", "")).decode("utf-8", errors="ignore")
                    except Exception:
                        title = current.get("title", "")

                    try:
                        desc = base64.b64decode(current.get("description", "")).decode("utf-8", errors="ignore")
                    except Exception:
                        desc = current.get("description", "")

                    start_ts = int(current.get("start_timestamp", 0))
                    stop_ts = int(current.get("stop_timestamp", 0))

                    start_time = time.strftime("%H:%M", time.localtime(start_ts)) if start_ts else "--:--"
                    end_time = time.strftime("%H:%M", time.localtime(stop_ts)) if stop_ts else "--:--"

                    self["epg_now_title"].setText(f"NOW: {title}")
                    self["epg_now_time"].setText(f"{start_time} - {end_time}")
                    self["epg_now_desc"].setText(desc)

                    # NEXT
                    if next_prog:
                        try:
                            next_title = base64.b64decode(next_prog.get("title", "")).decode("utf-8", errors="ignore")
                        except Exception:
                            next_title = next_prog.get("title", "")

                        try:
                            next_desc = base64.b64decode(next_prog.get("description", "")).decode("utf-8",
                                                                                                  errors="ignore")
                        except Exception:
                            next_desc = next_prog.get("description", "")

                        next_start_ts = int(next_prog.get("start_timestamp", 0))
                        next_stop_ts = int(next_prog.get("stop_timestamp", 0))

                        next_start = time.strftime("%H:%M", time.localtime(next_start_ts)) if next_start_ts else "--:--"
                        next_stop = time.strftime("%H:%M", time.localtime(next_stop_ts)) if next_stop_ts else "--:--"

                        self["epg_next_title"].setText(f"NEXT: {next_title}")
                        self["epg_next_time"].setText(f"{next_start} - {next_stop}")
                        self["epg_next_desc"].setText(next_desc)

                except Exception as e:
                    print(f"[CiefpStalkerFiles] EPG UI update error: {e}")
                    try:
                        self["info_icon"].hide()
                    except Exception:
                        pass

            self._epg_timer = eTimer()
            self._epg_timer.callback.append(_update_ui)
            self._epg_timer.start(10, True)

        except Exception as e:
            print(f"[CiefpStalkerFiles] EPG fetch error: {e}")
            try:
                self["info_icon"].hide()
            except Exception:
                pass

    def on_up(self):
        try:
            self["left_list"].up()
            self._update_info()
        except Exception:
            pass

    def on_down(self):
        try:
            self["left_list"].down()
            self._update_info()
        except Exception:
            pass

    def on_ok(self):
        idx = self["left_list"].getSelectedIndex()
        
        if self.current_category is None:
            if idx == 0:
                self.close()
                return
            if idx > 0 and (idx - 1) < len(self.categories):
                cat = self.categories[idx - 1]
                self.current_category = cat.get("category_id")
                self._load_streams_for_category()
            return

        if self.current_category is not None:
            if idx == 0:
                self.current_category = None
                self._render_categories()
                return

            if 0 < idx <= len(self.streams):
                now = time.time()
                
                if now - self.last_ok_time < 0.3:
                    return
                
                if idx == self.last_ok_index and (now - self.last_ok_time) < 1.5:
                    self._open_full_player(idx - 1)
                else:
                    self._play_preview(idx - 1)
                
                self.last_ok_time = now
                self.last_ok_index = idx

    def _play_preview(self, stream_idx):
        if not self.streams or stream_idx >= len(self.streams):
            return

        stream = self.streams[stream_idx]
        stream_id = stream.get("stream_id")
        title = stream.get("name", "Unknown")
        try:
            url = self.api.build_live_url(stream_id, "ts")
        except Exception as error:
            self["status"].setText("Stream link error: {}".format(error))
            return

        encoded_url = url.replace(":", "%3a")
        safe_title = title.replace(":", " -").replace("\n", " ")
        ref_str = f"{self.player_type_live}:0:1:0:0:0:0:0:0:0:{encoded_url}:{safe_title}"

        try:
            ref = eServiceReference(ref_str)
            if not ref.valid():
                self["status"].setText("Invalid service reference")
                return
        except Exception as e:
            self["status"].setText(f"Error: {e}")
            return

        try:
            self.session.nav.playService(ref)
            self.preview_ref = ref
            self.preview_active = True
            self["status"].setText(f"Preview: {title} (Press OK again for full screen)")
        except Exception as e:
            self["status"].setText(f"Play error: {e}")

    def _open_full_player(self, stream_idx):
        stream = self.streams[stream_idx]
        stream_id = stream.get("stream_id")
        title = stream.get("name", "Unknown")
        try:
            url = self.api.build_live_url(stream_id, "ts")
        except Exception as error:
            self["status"].setText("Stream link error: {}".format(error))
            return

        # Uzimamo EPG opis ako postoji
        epg_desc = getattr(self, "_current_epg_desc", "")

        # Kreiramo referencu na "čist" način (kao CiefpVideoPlayer)
        try:
            # Konvertujemo player_type u int (npr. "5001" -> 5001)
            service_type = int(self.player_type_live)
            ref = eServiceReference(service_type, 0, url)

            # Postavljamo naziv kanala (ovo će se prikazati kao veliki naslov)
            ref.setName(title)

            # Ako imamo EPG opis, možemo ga dodati u naziv (opciono)
            if epg_desc:
                # Spajamo naziv i EPG sa " | " ili novim redom
                # Probaj sa novim redom prvo, ako ne radi, koristi " | "
                combined_name = f"{title} | {epg_desc}"
                ref.setName(combined_name)

            if not ref.valid():
                self["status"].setText("Invalid service reference")
                return
        except Exception as e:
            self["status"].setText(f"Error: {e}")
            return

        self.session.openWithCallback(
            self._on_player_closed,
            MoviePlayer,
            ref
        )

    def _on_player_closed(self, *args):
        try:
            self._update_info()
            self["status"].setText("Returned to Live TV.")
        except Exception as e:
            print(f"[CiefpStalkerFiles] Return error: {e}")

    def open_epg(self):
        idx = self["left_list"].getSelectedIndex()
        if self.current_category is not None and 0 < idx <= len(self.streams):
            stream = self.streams[idx - 1]
            stream_id = stream.get("stream_id")
            channel_name = stream.get("name", "Unknown")

            from .epg_screen import EPGScreen
            self.session.open(EPGScreen, self.api, stream_id, channel_name)

    def open_settings(self):
        from .settings_screen import SettingsScreen
        self.session.open(SettingsScreen)

    def show_movies(self):
        self.session.open(
            MessageBox,
            "Movies are available in the Classic screen.\nPlease exit and choose Movies from the main menu.",
            MessageBox.TYPE_INFO, timeout=3
        )

    def show_series(self):
        self.session.open(
            MessageBox,
            "Series are available in the Classic screen.\nPlease exit and choose Series from the main menu.",
            MessageBox.TYPE_INFO, timeout=3
        )

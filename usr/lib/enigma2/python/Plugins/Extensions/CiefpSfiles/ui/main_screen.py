# -*- coding: utf-8 -*-
#
# main_screen.py - Glavni ekran za Filmove i Serije
#
from __future__ import absolute_import, print_function

import os
import threading
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from Screens.InfoBar import MoviePlayer
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from enigma import eTimer, eServiceReference

from Tools.LoadPixmap import LoadPixmap

from ..core.stalker_api import StalkerAPI
from ..core.metadata import fetch_metadata_async, fetch_omdb_rating_async, translate_text_async
from .settings_screen import SettingsScreen
from ..core.config import config
from .live_screen import LiveScreen
from .vod_groups_screen import VODGroupsScreen
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

class MainScreen(Screen):
    skin = """
        <screen name="CiefpSfilesMain" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <!-- NASLOV NA VRHU -->
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- LEVI PANEL: Kategorije i Streamovi -->
            <widget name="left_list" position="40,110" size="650,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- SREDNJI PANEL: Odvojeni podaci -->
            <widget name="movie_title" position="720,110" size="550,40" font="Bold;34"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="epg_title" position="720,150" size="550,30" font="Regular;20"
                    foregroundColor="#A0A0A0" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="duration" position="720,190" size="550,30" font="Regular;24"
                    foregroundColor="#D3D3D3" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="rating" position="720,230" size="550,30" font="Regular;24"
                    foregroundColor="#03a81f" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="imdb_rating" position="720,270" size="550,30" font="Regular;24"
                    foregroundColor="#F5C518" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="genres" position="720,310" size="550,30" font="Regular;24"
                    foregroundColor="#f702db" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="director" position="720,350" size="550,30" font="Regular;24"
                    foregroundColor="#f79102" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="plot" position="720,390" size="550,400" font="Regular;24"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>
            
            <widget name="cast_header" position="720,800" size="550,30" font="Bold;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="cast" position="720,840" size="550,120" font="Regular;20"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- DESNI PANEL: Poster -->
            <widget name="poster" position="1320,110" size="500,750"
                    alphatest="blend" zPosition="2"/>

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
            <eLabel text="INFO:SEARCH" position="1350,1000" size="300,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#00802d" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal, api_data):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        
        # Inicijalizacija API klijenta
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])
        
        self.current_view = "HOME" # HOME, VOD, SERIES
        self.categories = []
        self.streams = []
        self.current_category = None
        self.current_series = None
        self.current_season = None
        self.streams_series_data = None
        self._fetch_timer = None  
        self._last_tmdb_title = None 
        self._tmdb_timer = None

        # Tip plejera (učitava se iz config-a)
        self.player_type_vod = config.plugins.ciefpsfiles.player_type_vod.value

        # Widgets
        self["title"] = Label(f"..:: CiefpSfiles - {portal.get('name', '')} ::..")
        
        # Koristimo MenuList sa podrškom za sličice
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        
        # Srednji panel
        self["movie_title"] = Label("")
        self["epg_title"] = Label("")
        self["duration"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["plot"] = Label("")
        self["cast_header"] = Label("")
        self["cast"] = Label("")
        
        self["poster"] = Pixmap()
        self["status"] = Label("")

        # Actions
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions", "InfoActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.open_live_screen,
                "yellow": self.open_movies_groups,
                "blue": self.open_series_groups,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
                "menu": self.open_settings,
                "info": self.search_content,
                # "help": self.search_content,  # UKLONJENO
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        self._set_poster(None)
        self.show_home()

    def _set_poster(self, image_path):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if image_path and os.path.exists(image_path):
            path = image_path
        else:
            path = os.path.join(plugin_dir, "icons", "placeholder.png")

        px = _load_pixmap_safe(path)
        if px and self["poster"].instance:
            self["poster"].instance.setPixmap(px)

    def _clear_info_panel(self):
        self["movie_title"].setText("")
        self["epg_title"].setText("")
        self["duration"].setText("")
        self["rating"].setText("")
        self["imdb_rating"].setText("")
        self["genres"].setText("")
        self["director"].setText("")
        self["plot"].setText("")
        self["cast_header"].setText("")
        self["cast"].setText("")

    # ---------- VIEWS ----------
    def show_home(self):
        self.current_view = "HOME"
        self.current_category = None
        self._clear_info_panel()
        self._set_poster(None)

        items = []
        items.append([
            ("", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="Please select a category:")
        ])

        # --- LIVE ---
        icon_live = _get_icon_path("icon_live.png")
        if os.path.exists(icon_live):
            items.append([
                ("LIVE", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_live)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Live")
            ])
        else:
            items.append([("LIVE", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="> Live")])

        # --- MOVIES ---
        icon_film = _get_icon_path("icon_film.png")
        if os.path.exists(icon_film):
            items.append([
                ("MOVIES", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_film)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Movies")
            ])
        else:
            items.append([("MOVIES", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                                text="> Movies")])

        # --- SERIES ---
        icon_tv = _get_icon_path("icon_tv.png")
        if os.path.exists(icon_tv):
            items.append([
                ("SERIES", ""),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_tv)),
                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="> Series")
            ])
        else:
            items.append([("SERIES", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                                text="> Series")])

        items.append([("", ""),
                      MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                            text="")])
        items.append([("", ""),
                      MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                            text="or make settings on the settings button:")])
        items.append([("", ""),
                      MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                            text="TMDB, OMDB, Clear Cache ...")])

        self["left_list"].setList(items)
        self["plot"].setText(
            "Welcome to CiefpSfiles.\n\nPress GREEN for Live TV, YELLOW for Movies, or BLUE for Series.")

    def test_modern_vod(self):
        from .modern_vod_screen import ModernVODScreen
        # Uzimamo prvu VOD kategoriju za test
        if self.categories and self.current_view == "VOD":
            cat = self.categories[0]
            self.session.open(ModernVODScreen, self.portal, cat.get("category_id"), cat.get("category_name"))
        else:
            # Ako nismo u VOD, prvo učitajmo VOD kategorije
            ok, data, err = self.api.get_vod_categories()
            if ok and data:
                cat = data[0]
                self.session.open(ModernVODScreen, self.portal, cat.get("category_id"), cat.get("category_name"))

    def show_movies(self):
        self.current_view = "VOD"
        self.current_category = None
        self["status"].setText("Loading Movies categories...")
        ok, data, err = self.api.get_vod_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def show_series(self):
        self.current_view = "SERIES"
        self.current_category = None
        self["status"].setText("Loading Series categories...")
        ok, data, err = self.api.get_series_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def _render_categories(self):
        items = []
        # BACK dugme
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
        self["status"].setText(f"Loaded {len(self.categories)} categories. Press OK to open.")
        self._update_info()

    # ---------- NAVIGATION ----------
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

    def _update_info(self):
        idx = self["left_list"].getSelectedIndex()

        if self.current_view == "HOME":
            self._clear_info_panel()
            self._set_poster(None)
            return

        # Provera za BACK dugme
        if idx == 0:
            self._clear_info_panel()
            self["movie_title"].setText("Go back to previous menu.")
            # IZMENA: Ako smo u sezonama ili epizodama, NE brišemo poster!
            if not self.current_series:
                self._set_poster(None)
            return

        # 1. KATEGORIJE
        if self.current_category is None and (0 < idx <= len(self.categories)):
            cat = self.categories[idx - 1]
            self._clear_info_panel()
            self["movie_title"].setText(f"Category: {cat.get('category_name', '')}")
            self["plot"].setText("Press OK to open.")
            self._set_poster(None)
            return

        # 2. VOD ILI SERIJE (lista)
        if self.current_category is not None and not self.current_series:
            if 0 < idx <= len(self.streams):
                s = self.streams[idx - 1]
                name = clean_title(s.get("name", "Unknown"))
                rating = s.get("rating", "")

                self._clear_info_panel()
                self["movie_title"].setText(f"Name: {name}")

                if rating and str(rating) != "0":
                    self["rating"].setText(f"Server Rating: {rating}")

                if self.current_view == "VOD":
                    ext = s.get("container_extension", "")
                    if ext:
                        self["duration"].setText(f"Format: {ext.upper()}")

                self["plot"].setText("Loading metadata...")

                if self.current_view in ("VOD", "SERIES"):
                    self._trigger_tmdb_fetch(name, "movie" if self.current_view == "VOD" else "tv")
                else:
                    self["plot"].setText("Press OK to play.")
                    self._set_poster(None)
            return

        # 3. SERIJE (Sezone)
        if self.current_series is not None and self.current_season is None:
            series_info = self.current_series.get("info", {})
            base_name = series_info.get("name", "Unknown Series")
            if 0 < idx <= len(self.streams):
                season_num = self.streams[idx - 1]
                self._clear_info_panel()
                self["movie_title"].setText(f"Series: {base_name}")
                self["plot"].setText(f"Season {season_num}\nSelect an episode to play.")
            return

        # 4. SERIJE (Epizode)
        if self.current_series is not None and self.current_season is not None:
            series_info = self.current_series.get("info", {})
            base_name = series_info.get("name", "Unknown Series")
            if 0 < idx <= len(self.streams):
                ep = self.streams[idx - 1]
                ep_num = ep.get("episode_num")
                title = ep.get("title", "Unknown")
                self._clear_info_panel()
                self["movie_title"].setText(f"Series: {base_name}")
                self["plot"].setText(f"S{self.current_season}E{ep_num} - {title}\n\nPress OK to play.")
            return

    def _trigger_tmdb_fetch(self, title, media_type):
        if title == self._last_tmdb_title:
            return

        self._last_tmdb_title = title

        from enigma import eTimer
        def _do_fetch():
            fetch_metadata_async(title, media_type, self._on_tmdb_data)

        if self._tmdb_timer:
            self._tmdb_timer.stop()

        self._tmdb_timer = eTimer()
        self._tmdb_timer.callback.append(_do_fetch)
        self._tmdb_timer.start(500, True)

    def _on_tmdb_data(self, success, data):
        from enigma import eTimer
        def _update_ui():
            if not success:
                self["plot"].setText(f"TMDB Error: {data}")
                return

            # DODAJTE OVU LINIJU:
            self._current_poster_path = data.get("poster_path")

            plot = data.get("plot", "-")
            if len(plot) > 450:
                plot = plot[:450] + "..."

            self["plot"].setText(f"Plot:\n{plot}")
            
            if config.plugins.ciefpsfiles.groq_plot_translation.value:
                self["plot"].setText(f"Plot:\n{plot}\n\n(Translating...)")
                translate_text_async(plot, self._on_translated_plot)
            else:
                self["plot"].setText(f"Plot:\n{plot}")

            self["movie_title"].setText(f"{data.get('title')} ({data.get('year')})")
            self["epg_title"].setText("")
            self["rating"].setText(f"TMDB: {data.get('rating')}/10 ★")
            self["genres"].setText(f"Genres: {data.get('genres')}")
            self["director"].setText(f"Director: {data.get('director')}")
            
            cast = data.get('cast', '-')
            if cast != '-':
                self["cast_header"].setText("Cast:")
                self["cast"].setText(cast)
            else:
                self["cast_header"].setText("")
                self["cast"].setText("")

            self["duration"].setText("")
            self["imdb_rating"].setText("IMDB: Loading...")

            fetch_omdb_rating_async(data.get('title'), data.get('year'), self._on_omdb_data)
            self._set_poster(data.get("poster_path"))

        self._tmdb_ui_timer = eTimer()
        self._tmdb_ui_timer.callback.append(_update_ui)
        self._tmdb_ui_timer.start(10, True)

    def _on_omdb_data(self, success, rating):
        from enigma import eTimer
        def _update_ui():
            if success:
                self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
            else:
                self["imdb_rating"].setText("IMDB: N/A")

        self._omdb_ui_timer = eTimer()
        self._omdb_ui_timer.callback.append(_update_ui)
        self._omdb_ui_timer.start(10, True)

    def _on_translated_plot(self, success, translated_text):
        from enigma import eTimer
        def _update_ui():
            if success:
                # Uzimamo trenutni jezik iz config-a da prikažemo tačan naziv
                try:
                    from ..core.config import config
                    lang = config.plugins.ciefpsfiles.translate_language.value.upper()
                except Exception:
                    lang = "PREVOD"

                # Prikazujemo npr. "Plot (TR):" ili "Plot (SR):"
                self["plot"].setText(f"Plot ({lang}):\n{translated_text}")
            else:
                current_text = self["plot"].getText()
                if "(Translating...)" in current_text:
                    self["plot"].setText(
                        current_text.replace("(Translating...)", f"(Prevod nije uspeo: {translated_text})"))
                else:
                    self["plot"].setText(current_text + f"\n\n(Prevod nije uspeo: {translated_text})")

        self._trans_timer = eTimer()
        self._trans_timer.callback.append(_update_ui)
        self._trans_timer.start(10, True)

    # ---------- ACTIONS ----------
    def on_ok(self):
        idx = self["left_list"].getSelectedIndex()

        if self.current_view == "HOME":
            if idx == 1:
                self.open_live_screen()
            elif idx == 2:
                self.open_movies_groups()
            elif idx == 3:
                self.open_series_groups()
            return

        if self.current_category is None:
            if idx == 0:
                self.show_home()
                return
            if idx > 0 and (idx - 1) < len(self.categories):
                cat = self.categories[idx - 1]
                self.current_category = cat.get("category_id")
                self._load_streams_for_category()
            return

        if self.current_category is not None:
            if idx == 0:
                if self.current_season is not None:
                    self._open_series(self.streams_series_data)
                    return
                elif self.current_series is not None:
                    self.current_series = None
                    self._load_streams_for_category()
                    return
                else:
                    self.current_category = None
                    self._render_categories()
                    return

            if self.current_view == "SERIES" and not self.current_series:
                if idx > 0 and (idx - 1) < len(self.streams):
                    self._open_series(self.streams[idx - 1])
            elif self.current_view == "SERIES" and self.current_series and not self.current_season:
                if idx > 0 and (idx - 1) < len(self.streams):
                    season_num = self.streams[idx - 1]
                    self._open_season(season_num)
            else:
                self._play_selected_stream()

    def _load_streams_for_category(self):
        self["status"].setText("Loading streams...")
        if self.current_view == "VOD":
            ok, data, err = self.api.get_vod_streams(self.current_category)
        elif self.current_view == "SERIES":
            ok, data, err = self.api.get_series(self.current_category)
        else:
            return

        if ok:
            self.streams = data
            items = []
            
            # BACK dugme
            items.append([
                ("BACK", ""),
                MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text="[ BACK TO CATEGORIES ]")
            ])

            if self.current_view == "SERIES":
                icon = _get_icon_path("icon_tv.png")
            else:
                icon = _get_icon_path("icon_film.png")

            for s in self.streams:
                name = clean_title(s.get("name", "Unknown"))
                if os.path.exists(icon):
                    items.append([
                        (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                        MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon)),
                        MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=name)
                    ])
                else:
                    items.append([
                        (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                        MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=name)
                    ])

            self["left_list"].setList(items)
            self["left_list"].moveToIndex(0)
            self["status"].setText(f"Loaded {len(self.streams)} items.")
            self._update_info()
        else:
            self["status"].setText(f"Error: {err}")

    def _play_selected_stream(self):
        idx = self["left_list"].getSelectedIndex()
        if idx == 0:
            return

        stream = self.streams[idx - 1]

        try:
            if self.current_view == "SERIES" and self.current_season is not None:
                ep_id = stream.get("id")
                ext = stream.get("container_extension", "mp4")
                url = self.api.build_series_url(ep_id, ext)
                title = stream.get("title", "Unknown")
            elif self.current_view == "VOD":
                stream_id = stream.get("stream_id")
                title = stream.get("name", "Unknown")
                container_ext = stream.get("container_extension", "mp4")
                url = self.api.build_movie_url(stream_id, container_ext)
            else:
                return
        except Exception as error:
            self["status"].setText("Stream link error: {}".format(error))
            return

        self["status"].setText(f"Playing: {title}...")

        encoded_url = url.replace(":", "%3a")
        safe_title = title.replace(":", " -").replace("\n", " ")
        ref_str = f"{self.player_type_vod}:0:1:0:0:0:0:0:0:0:{encoded_url}:{safe_title}"

        try:
            ref = eServiceReference(ref_str)
            if not ref.valid():
                self["status"].setText("Invalid service reference")
                return
        except Exception as e:
            self["status"].setText(f"Error: {e}")
            return

        try:
            self.session.openWithCallback(
                self._on_stream_player_closed,
                MoviePlayer,
                ref
            )
        except Exception as e:
            self["status"].setText(
                "Could not open player: {}".format(e)
            )
            print("[CiefpSfiles] MoviePlayer error: {}".format(e))

    def _open_series(self, series_data):
        series_id = series_data.get("series_id")
        series_name = series_data.get("name", "Unknown")

        # DODAJTE OVE DVE LINIJE:
        self._saved_poster = getattr(self, '_current_poster_path', None)
        self._saved_series_name = series_name

        self["status"].setText(f"Loading seasons for {series_name}...")

        def fetch_worker():
            ok, data, err = self.api.get_series_info(series_id)
            from enigma import eTimer
            def _update_ui():
                self._fetch_timer = None
                if not ok or not data:
                    self["status"].setText(f"Error loading series: {err}")
                    return
                self.current_series = data
                self.streams_series_data = series_data
                self.current_season = None
                self.streams = []

                items = []
                # BACK dugme
                items.append([
                    ("BACK", ""),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text="[ BACK TO SERIES ]")
                ])
                icon_season = _get_icon_path("icon_season.png")
                episodes_raw = data.get("episodes", {})

                # --- DODATO: Normalizacija podataka (rečnik vs lista) ---
                episodes = {}
                if isinstance(episodes_raw, dict):
                    # Provajder vraća rečnik, sve je u redu
                    episodes = episodes_raw
                elif isinstance(episodes_raw, list):
                    # Provajder vraća listu, moramo je grupisati po sezonama
                    for ep in episodes_raw:
                        season = str(ep.get("season", "1"))
                        if season not in episodes:
                            episodes[season] = []
                        episodes[season].append(ep)
                # ---------------------------------------------------------

                if not episodes:
                    items.append([("NONE", ""), MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="No episodes found.")])
                else:
                    # Sada je bezbedno pozvati .keys() jer smo osigurali da je 'episodes' rečnik
                    for season_num in sorted(episodes.keys(), key=int):
                        season_text = f"Season {season_num}"
                        if os.path.exists(icon_season):
                            items.append([
                                (season_text, str(season_num)),
                                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_season)),
                                MultiContentEntryText(pos=(50, 0), size=(650, 50), font=0,
                                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                      text=season_text)
                            ])
                        else:
                            items.append([
                                (season_text, str(season_num)),
                                MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                      text=season_text)
                            ])
                        self.streams.append(season_num)

                self["left_list"].setList(items)
                if len(items) > 1:
                    self["left_list"].moveToIndex(1)
                else:
                    self["left_list"].moveToIndex(0)
                self["status"].setText(f"Loaded {len(episodes)} seasons.")

                # DODAJTE OVO:
                self["movie_title"].setText(f"Series: {series_name}")
                if self._saved_poster:
                    self._set_poster(self._saved_poster)
                else:
                    self._set_poster(None)

                self._update_info()

            self._fetch_timer = eTimer()
            self._fetch_timer.callback.append(_update_ui)
            self._fetch_timer.start(10, True)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _open_season(self, season_num):
        self.current_season = str(season_num)
        episodes = self.current_series.get("episodes", {}).get(self.current_season, [])

        items = []
        # BACK dugme
        items.append([
            ("BACK", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO SEASONS ]")
        ])
        
        self.streams = []
        icon_play = _get_icon_path("icon_play.png")

        for ep in episodes:
            ep_num = ep.get("episode_num")
            title = ep.get("title", "Unknown")
            ep_text = f"S{season_num}E{ep_num} - {title}"
            
            if os.path.exists(icon_play):
                items.append([
                    (ep_text, ep.get("id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_play)),
                    MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=ep_text)
                ])
            else:
                items.append([
                    (ep_text, ep.get("id")),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=ep_text)
                ])
            self.streams.append(ep)

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Loaded {len(episodes)} episodes for Season {season_num}.")

        # Prvo osvežite info panel (koji sada neće obrisati poster)
        self._update_info()

        # Zatim forsirajte poster i naslov
        self["movie_title"].setText(f"Series: {self._saved_series_name}")
        if self._saved_poster:
            self._set_poster(self._saved_poster)
        else:
            self._set_poster(None)

    def search_content(self):
        # Pretraga radi samo kada smo u listi filmova ili serija (ne u kategorijama)
        if self.current_category is None:
            self.session.open(
                MessageBox,
                "Search is available only within a category (Movies or Series).",
                MessageBox.TYPE_INFO, timeout=3
            )
            return

        def do_search(search_term):
            if not search_term:
                return

            # Pretvaramo u mala slova za lakšu pretragu
            search_term = search_term.lower()

            # Filtriramo trenutnu listu streamova
            filtered_streams = []
            for s in self.streams:
                name = s.get("name", "").lower()
                if search_term in name:
                    filtered_streams.append(s)

            if not filtered_streams:
                self.session.open(
                    MessageBox,
                    f"No results for: '{search_term}'",
                    MessageBox.TYPE_INFO, timeout=3
                )
                return

            # Prikazujemo filtrirane rezultate
            self.streams = filtered_streams
            self._render_filtered_streams()

        # Otvaramo virtuelnu tastaturu
        self.session.openWithCallback(
            do_search,
            VirtualKeyBoard,
            title="Search",
            text=""
        )

    def _render_filtered_streams(self):
        """Pomoćna funkcija za prikaz filtriranih rezultata."""
        items = []
        items.append([
            ("BACK", ""),
            MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO CATEGORIES ]")
        ])

        if self.current_view == "SERIES":
            icon = _get_icon_path("icon_tv.png")
        else:
            icon = _get_icon_path("icon_film.png")

        for s in self.streams:
            name = s.get("name", "Unknown")
            if os.path.exists(icon):
                items.append([
                    (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon)),
                    MultiContentEntryText(pos=(50, 0), size=(600, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
            else:
                items.append([
                    (name, s.get("stream_id") if "stream_id" in s else s.get("series_id")),
                    MultiContentEntryText(pos=(0, 0), size=(650, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Found {len(self.streams)} results.")
        self._update_info()

    def _on_stream_player_closed(self, *args):
        try:
            self._update_info()
            self["status"].setText("Returned to CiefpSfiles.")
        except Exception as e:
            print("[CiefpSfiles] Return error: {}".format(e))

    def open_settings(self):
        self.session.open(SettingsScreen)
        
    def open_live_screen(self):
        self.session.open(LiveScreen, self.portal, None)

    def open_movies_groups(self):
        skin_type = config.plugins.ciefpsfiles.skin_type.value
        if skin_type == "modern":
            from .vod_groups_screen import VODGroupsScreen
            self.session.open(VODGroupsScreen, self.portal)
        else:
            # Classic - otvori stari prikaz za filmove
            self.show_movies()

    def open_series_groups(self):
        skin_type = config.plugins.ciefpsfiles.skin_type.value
        if skin_type == "modern":
            from .series_groups_screen import SeriesGroupsScreen
            self.session.open(SeriesGroupsScreen, self.portal)
        else:
            self.show_series()

# -*- coding: utf-8 -*-
#
# modern_seasons_screen.py - Moderni ekran za sezone i epizode
#
from __future__ import absolute_import, print_function

import os
import threading
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from enigma import eTimer, eServiceReference, eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap

from ..core.metadata import fetch_metadata_async, fetch_omdb_rating_async, fetch_episode_metadata_async
from ..core.paths import POSTERS_CACHE_DIR
from ..core.stalker_api import StalkerAPI
from ..core.config import config

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

def _download_image_async(url, cache_filename, callback):
    def worker():
        path = os.path.join(POSTERS_CACHE_DIR, cache_filename)
        if os.path.exists(path):
            callback(path)
            return
        try:
            import urllib.request
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                with open(path, 'wb') as f:
                    f.write(resp.read())
            callback(path)
        except Exception as e:
            print(f"[CiefpSfiles] Image download error: {e}")
            callback(None)
    threading.Thread(target=worker, daemon=True).start()

class ModernSeasonsScreen(Screen):
    skin = """
        <screen name="CiefpSfilesModernSeasons" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- LEVI PANEL: Sezone / Epizode -->
            <widget name="left_list" position="40,110" size="480,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- SREDNJI PANEL: Informacije o seriji -->
            <widget name="movie_title" position="550,110" size="550,40" font="Bold;34"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="rating" position="550,180" size="550,30" font="Regular;24"
                    foregroundColor="#03a81f" backgroundColor="#011a2e" transparent="1"/>

            <widget name="imdb_rating" position="550,220" size="550,30" font="Regular;24"
                    foregroundColor="#F5C518" backgroundColor="#011a2e" transparent="1"/>

            <widget name="genres" position="550,260" size="550,30" font="Regular;24"
                    foregroundColor="#f702db" backgroundColor="#011a2e" transparent="1"/>

            <widget name="director" position="550,300" size="550,30" font="Regular;24"
                    foregroundColor="#f79102" backgroundColor="#011a2e" transparent="1"/>

            <widget name="plot" position="550,340" size="550,300" font="Regular;24"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- DONJI PANEL: Glumci (slike) -->
            <widget name="cast_header" position="550,640" size="550,30" font="Bold;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="cast_img_0" position="550,670" size="160,240" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_1" position="720,670" size="160,240" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_2" position="890,670" size="160,240" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_3" position="1060,670" size="160,240" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_4" position="1230,670" size="160,240" alphatest="blend" zPosition="3"/>

            <widget name="cast_name_0" position="550,920" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_1" position="720,920" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_2" position="890,920" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_3" position="1060,920" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_4" position="1230,920" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <!-- DESNI PANEL: Poster -->
            <widget name="logo" position="1410,110" size="500,750"
                    alphatest="blend" zPosition="2"/>

            <!-- STATUS (Pomeren dole levo) -->
            <widget name="status" position="500,1005" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>

            <ePixmap pixmap="buttons/green.png" position="240,1005" size="35,35" alphatest="blend"/>
            <eLabel text="PLAY" position="290,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal, series_id, series_title, poster_path=None, tmdb_data=None):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        self.series_id = series_id
        self.series_title = series_title
        self.poster_path = poster_path
        self.tmdb_data = tmdb_data or {}

        # ISPRAVKA: Izvuci TMDB ID iz prosleđenih podataka
        self.tmdb_id = self.tmdb_data.get("id") or self.tmdb_data.get("tmdb_id")
        print(f"[CiefpSfiles DEBUG] TMDB ID za serije: {self.tmdb_id}")

        # OVA LINIJA JE NEDOSTAJALA:
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])

        self.seasons = []
        self.episodes = []
        self.current_season = None
        self.is_showing_episodes = False
        
        try:
            self.player_type_vod = config.plugins.ciefpsfiles.player_type_vod.value
        except Exception:
            self.player_type_vod = "4097"
        
        self["title"] = Label(f"..:: {series_title} ::..")
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        self["logo"] = Pixmap()
        self["movie_title"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["plot"] = Label("")
        self["cast_header"] = Label("")

        # Obrišite staro: self["cast"] = Label("")
        # I dodajte ovo:
        for i in range(5):
            self["cast_img_%d" % i] = Pixmap()
            self["cast_name_%d" % i] = Label("")
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.on_back,
                "red": self.on_back,
                "green": self.on_ok,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Prvo pokušaj da učitaš poster serije
        if self.poster_path and os.path.exists(self.poster_path):
            px = _load_pixmap_safe(self.poster_path)
            if px and self["logo"].instance:
                self["logo"].instance.setPixmap(px)
                self["logo"].show()
        else:
            # Ako nema postera, koristi plugin logo
            logo_path = os.path.join(plugin_dir, "icons", "plugin_logo.png")
            if os.path.exists(logo_path):
                px = _load_pixmap_safe(logo_path)
                if px and self["logo"].instance:
                    self["logo"].instance.setPixmap(px)
                    self["logo"].show()

        self["status"].setText("Loading seasons...")
        self._fetch_metadata()
        self["status"].setText("Loading seasons...")
        self.load_seasons()
        # DODAJ OVU LINIJU:
        self._on_selection_changed()
        
    def load_seasons(self):
        ok, data, err = self.api.get_series_info(self.series_id)
        if ok and data:
            episodes_raw = data.get("episodes", {})

            # --- UNIVERZALNA ZAŠTITA ---
            episodes = {}
            if isinstance(episodes_raw, dict):
                episodes = episodes_raw
            elif isinstance(episodes_raw, list):
                for ep in episodes_raw:
                    # Proveravamo da li je 'ep' rečnik pre nego što pozovemo .get()
                    if isinstance(ep, dict):
                        season = str(ep.get("season", "1"))
                        if season not in episodes:
                            episodes[season] = []
                        episodes[season].append(ep)
                    # Ako je ep lista (neki provajderi šalju liste unutar liste),
                    # ignorišemo je ili je možete ručno mapirati ako znate indekse
            # ---------------------------------------------------------

            if not episodes:
                self["status"].setText("No seasons found.")
                return

            self.seasons = sorted(episodes.keys(), key=int)
            self.is_showing_episodes = False
            self.render_seasons()
        else:
            self["status"].setText(f"Error: {err}")

    def render_seasons(self):
        items = []
        icon_season = _get_icon_path("icon_season.png")

        for idx, season_num in enumerate(self.seasons):
            text = f"Season {season_num}"
            if os.path.exists(icon_season):
                items.append([
                    (season_num, "season"),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_season)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
            else:
                items.append([
                    (season_num, "season"),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Loaded {len(self.seasons)} seasons. Press OK to open.")

        # ODMAH povuci opis za prvu sezonu (kao u klasičnom)
        if self.seasons and self.tmdb_id:
            season_num = self.seasons[0]
            self["plot"].setText(f"Season {season_num}\n\nLoading metadata...")

            def _on_season_meta(success, data):
                def _set_text():
                    if success:
                        self["plot"].setText(f"Season {season_num}\n\n{data.get('plot')}")
                    else:
                        self["plot"].setText(f"Season {season_num}\nSelect an episode to play.")

                t = eTimer()
                t.callback.append(_set_text)
                t.start(10, True)

            fetch_episode_metadata_async(self.tmdb_id, season_num, 1, _on_season_meta)

    def load_episodes(self, season_num):
        ok, data, err = self.api.get_series_info(self.series_id)
        if ok and data:
            episodes_raw = data.get("episodes", {})

            # --- UNIVERZALNA ZAŠTITA ---
            episodes = {}
            if isinstance(episodes_raw, dict):
                episodes = episodes_raw
            elif isinstance(episodes_raw, list):
                for ep in episodes_raw:
                    if isinstance(ep, dict):
                        season = str(ep.get("season", "1"))
                        if season not in episodes:
                            episodes[season] = []
                        episodes[season].append(ep)
            # ---------------------------------------

            episodes_data = episodes.get(str(season_num), [])
            self.episodes = episodes_data
            self.current_season = season_num
            self.is_showing_episodes = True
            self.render_episodes()
        else:
            self["status"].setText(f"Error: {err}")

    def render_episodes(self):
        items = []
        icon_play = _get_icon_path("icon_play.png")

        # BACK dugme
        items.append([
            ("BACK", "back"),
            MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                  text="[ BACK TO SEASONS ]")
        ])

        # Postavljamo episode_num ručno
        for i, ep in enumerate(self.episodes):
            if not ep.get("episode_num"):
                ep["episode_num"] = i + 1

            ep_num = ep.get("episode_num")
            title = ep.get("title", "Unknown")
            text = f"S{self.current_season}E{ep_num} - {title}"

            if os.path.exists(icon_play):
                items.append([
                    (ep, "episode"),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_play)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])
            else:
                items.append([
                    (ep, "episode"),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=text)
                ])

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Season {self.current_season}: {len(self.episodes)} episodes.")

        # ODMAH povuci opis za prvu epizodu (kao u klasičnom)
        if self.episodes and self.tmdb_id:
            ep = self.episodes[0]
            ep_num = ep.get("episode_num")
            title = ep.get("title", "Unknown")
            self["plot"].setText(f"S{self.current_season}E{ep_num} - {title}\n\nLoading metadata...")

            def _on_ep_meta(success, data):
                def _set_text():
                    if success:
                        self["plot"].setText(
                            f"S{self.current_season}E{ep_num} - {data.get('title')}\n\n{data.get('plot')}")
                    else:
                        self["plot"].setText(f"S{self.current_season}E{ep_num} - {title}\n\nPress OK to play.")

                t = eTimer()
                t.callback.append(_set_text)
                t.start(10, True)

            fetch_episode_metadata_async(self.tmdb_id, self.current_season, ep_num, _on_ep_meta)

    def on_up(self):
        try:
            self["left_list"].up()
            self._on_selection_changed()
        except Exception:
            pass

    def on_down(self):
        try:
            self["left_list"].down()
            self._on_selection_changed()
        except Exception:
            pass

    def _on_selection_changed(self):
        idx = self["left_list"].getSelectedIndex()

        if not self.is_showing_episodes:
            # Lista sezona
            if 0 <= idx < len(self.seasons):
                season_num = self.seasons[idx]
                self._update_plot_for_selection(season_num)
        else:
            # Lista epizoda
            if 0 < idx <= len(self.episodes):
                ep = self.episodes[idx - 1]
                ep_num = ep.get("episode_num")

                # Ako iz nekog razloga episode_num nije postavljen, uzimamo indeks
                if ep_num is None:
                    ep_num = idx

                self._update_plot_for_selection(self.current_season, ep_num)

    def on_ok(self):
        idx = self["left_list"].getSelectedIndex()
        
        if not self.is_showing_episodes:
            # Kliknuta je sezona
            if 0 <= idx < len(self.seasons):
                season_num = self.seasons[idx]
                self.load_episodes(season_num)
        else:
            # Kliknuta je epizoda ili BACK
            if idx == 0:
                # BACK
                self.is_showing_episodes = False
                self.current_season = None
                self.render_seasons()
                return
            
            if 0 < idx <= len(self.episodes):
                ep = self.episodes[idx - 1]
                self.play_episode(ep)

    def play_episode(self, ep):
        ep_id = ep.get("id")
        title = ep.get("title", "Unknown")
        ext = ep.get("container_extension", "mp4")
        
        try:
            url = self.api.build_series_url(ep_id, ext)
        except Exception as error:
            self["status"].setText("Episode link error: {}".format(error))
            return
        
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
                self._on_player_closed,
                MoviePlayer,
                ref
            )
        except Exception as e:
            self["status"].setText(f"Could not open player: {e}")

    def _on_player_closed(self, *args):
        self["status"].setText("Returned to series.")

    def _fetch_metadata(self):
        # Preuzimamo TMDB podatke za seriju na osnovu njenog naslova
        def _do_fetch():
            fetch_metadata_async(self.series_title, "tv", self._on_tmdb_data)

        self._tmdb_timer = eTimer()
        self._tmdb_timer.callback.append(_do_fetch)
        self._tmdb_timer.start(300, True)

    def _on_tmdb_data(self, success, data):
        def _update_ui():
            if not success or not data:
                self["plot"].setText("TMDB Metadata not found.")
                return

            self["movie_title"].setText(f"{data.get('title', 'Unknown')} ({data.get('year', '')})")
            self["rating"].setText(f"TMDB: {data.get('rating', '0.0')}/10 ★")
            self["genres"].setText(f"Genres: {data.get('genres', '-')}")
            self["director"].setText(f"Creator: {data.get('director', '-')}")
            # Proveravamo da li je korisnik već ušao u epizode.
            # Ako jeste, NE diramo plot, jer je tamo već opis epizode.
            if not self.is_showing_episodes and self.current_season is None:
                plot = data.get("plot", "-")
                if len(plot) > 450:
                    plot = plot[:450] + "..."
                self["plot"].setText(f"Plot:\n{plot}")

            self["imdb_rating"].setText("IMDB: Loading...")
            fetch_omdb_rating_async(data.get('title'), data.get('year'), self._on_imdb_data)

            # --- DODATO ZA SLIKE GLUMACA ---
            cast_list = data.get("cast_data", [])
            if cast_list:
                self["cast_header"].setText("Cast:")
                for i in range(5):
                    if i < len(cast_list):
                        actor = cast_list[i]
                        name = actor.get("name", "Unknown")
                        profile_path = actor.get("profile_path")

                        self["cast_name_%d" % i].setText(name)

                        if profile_path:
                            url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                            filename = f"actor_{profile_path.split('/')[-1]}"

                            def cb(path, idx=i):
                                if path:
                                    px = _load_pixmap_safe(path)
                                    if px and self["cast_img_%d" % idx].instance:
                                        self["cast_img_%d" % idx].instance.setPixmap(px)
                                        self["cast_img_%d" % idx].show()

                            _download_image_async(url, filename, cb)
                    else:
                        self["cast_name_%d" % i].setText("")
            else:
                self["cast_header"].setText("")

        self._tmdb_ui_timer = eTimer()
        self._tmdb_ui_timer.callback.append(_update_ui)
        self._tmdb_ui_timer.start(10, True)

    def _update_plot_for_selection(self, season_num, episode_num=None):
        if not self.tmdb_id:
            self["plot"].setText("Plot:\nOpis nije dostupan (Nema TMDB ID).")
            return

        import re
        s_clean = re.sub(r'\D', '', str(season_num))
        if not s_clean:
            s_clean = "1"

        ep_clean = None
        if episode_num is not None:
            ep_clean = re.sub(r'\D', '', str(episode_num))
            if not ep_clean:
                ep_clean = "1"

        target_ep = ep_clean if ep_clean else "1"
        self["plot"].setText("Plot:\nLoading...")

        # Direktan poziv preko standardne funkcije iz metadata.py bez kompleksnih tajmera koji blokiraju
        from ..core.metadata import _get_api_key, _fetch_json

        def worker():
            api_key = _get_api_key()
            plot_text = "No description available."
            if api_key and self.tmdb_id:
                url = f"https://api.themoviedb.org/3/tv/{self.tmdb_id}/season/{s_clean}/episode/{target_ep}?api_key={api_key}&language=en-US"
                data = _fetch_json(url)
                if data and isinstance(data, dict):
                    overview = data.get("overview")
                    if overview:
                        plot_text = overview

            def update_ui():
                self["plot"].setText(f"Plot:\n{plot_text}")

            from enigma import eTimer
            self._plot_timer = eTimer()
            self._plot_timer.callback.append(update_ui)
            self._plot_timer.start(10, True)

        threading.Thread(target=worker, daemon=True).start()

    def _on_imdb_data(self, success, rating):
        def _update_ui():
            if success:
                self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
            else:
                self["imdb_rating"].setText("IMDB: N/A")

        self._imdb_ui_timer = eTimer()
        self._imdb_ui_timer.callback.append(_update_ui)
        self._imdb_ui_timer.start(10, True)

    def on_back(self):
        if self.is_showing_episodes:
            # Vrati se na sezone
            self.is_showing_episodes = False
            self.current_season = None
            self.render_seasons()
        else:
            # Zatvori ekran
            self.close()
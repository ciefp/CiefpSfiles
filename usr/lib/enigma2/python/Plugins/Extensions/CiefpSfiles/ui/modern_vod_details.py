# -*- coding: utf-8 -*-
#
# modern_vod_details.py - Detaljni ekran za filmove sa slikama glumaca
#
from __future__ import absolute_import, print_function

import os
import threading
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from enigma import eTimer, eServiceReference, ePoint
from Tools.LoadPixmap import LoadPixmap

from ..core.stalker_api import StalkerAPI
from ..core.config import config
from ..core.paths import POSTERS_CACHE_DIR
from ..core.metadata import translate_text_async
from ..core.metadata import translate_text_async, fetch_omdb_rating_async

def _load_pixmap_safe(path):
    if path and os.path.exists(path):
        try:
            return LoadPixmap(path)
        except Exception:
            return None
    return None

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

class ModernVODDetailsScreen(Screen):
    skin = """
        <screen name="CiefpSfilesModernVODDetails" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <!-- SREDNJI PANEL: Informacije -->
            <widget name="movie_title" position="720,110" size="550,40" font="Bold;34"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="rating" position="650,230" size="550,30" font="Regular;24"
                    foregroundColor="#03a81f" backgroundColor="#011a2e" transparent="1"/>

            <widget name="imdb_rating" position="650,270" size="550,30" font="Regular;24"
                    foregroundColor="#F5C518" backgroundColor="#011a2e" transparent="1"/>

            <widget name="genres" position="650,310" size="550,30" font="Regular;24"
                    foregroundColor="#f702db" backgroundColor="#011a2e" transparent="1"/>

            <widget name="director" position="650,350" size="550,30" font="Regular;24"
                    foregroundColor="#f79102" backgroundColor="#011a2e" transparent="1"/>

            <widget name="plot" position="650,390" size="600,350" font="Regular;24"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- LEVI PANEL ISPOD PLOT-A: Slika režisera i tekstualni spisak glumaca -->
            <widget name="director_img" position="100,200" size="185,278" alphatest="blend" zPosition="3"/>
            <widget name="director_name" position="100,500" size="200,40" font="Bold;24" halign="left" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="cast_text" position="350,200" size="300,400" font="Regular;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- DESNI PANEL: Veliki Poster -->
            <widget name="poster" position="1320,110" size="500,750"
                    alphatest="blend" zPosition="2"/>

            <!-- DONJI PANEL: Glumci (slike) - POMERENO NAGORE -->
            <widget name="cast_header" position="40,720" size="900,30" font="Bold;24"
                    foregroundColor="#00FFFF" backgroundColor="#011a2e" transparent="1"/>

            <widget name="cast_img_0" position="40,700" size="185,278" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_1" position="235,700" size="185,278" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_2" position="430,700" size="185,278" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_3" position="625,700" size="185,278" alphatest="blend" zPosition="3"/>
            <widget name="cast_img_4" position="820,700" size="185,278" alphatest="blend" zPosition="3"/>

            <widget name="cast_name_0" position="40,990" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_1" position="235,990" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_2" position="430,990" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_3" position="625,990" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            <widget name="cast_name_4" position="820,990" size="160,40" font="Regular;18" halign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="1300,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="1350,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>

            <ePixmap pixmap="buttons/green.png" position="1540,1005" size="35,35" alphatest="blend"/>
            <eLabel text="PLAY" position="1590,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal, stream_data, tmdb_data):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        self.stream_data = stream_data
        self.tmdb_data = tmdb_data
        
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])
        try:
            self.player_type_vod = config.plugins.ciefpsfiles.player_type_vod.value
        except Exception:
            self.player_type_vod = "4097"

        self["title"] = Label(f"..:: {tmdb_data.get('title', 'Details')} ::..")
        self["movie_title"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["plot"] = Label("")
        self["status"] = Label("")
        self["poster"] = Pixmap()
        self["cast_header"] = Label("")   # <-- DODATO
        self["director_img"] = Pixmap()
        self["director_name"] = Label("")
        self["cast_text"] = Label("")
        
        for i in range(5):
            self["cast_img_%d" % i] = Pixmap()
            self["cast_name_%d" % i] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.play_movie,
                "ok": self.play_movie,
            }, -1
        )
        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        # 1. Popunjavamo tekstualne podatke iz onoga što je Modern VOD već preuzeo
        self["movie_title"].setText(f"{self.tmdb_data.get('title', 'Unknown')} ({self.tmdb_data.get('year', '')})")
        self["rating"].setText(f"TMDB: {self.tmdb_data.get('rating', '0.0')}/10 ★")
        self["genres"].setText(f"Genres: {self.tmdb_data.get('genres', '-')}")
        self["director"].setText(f"Director: {self.tmdb_data.get('director', '-')}")
        
        plot = self.tmdb_data.get("plot", "-")
        if len(plot) > 450:
            plot = plot[:450] + "..."
        self["plot"].setText(f"Plot:\n{plot}")

        self["imdb_rating"].setText("IMDB: Loading...")

        # DODAJ OVO:
        fetch_omdb_rating_async(self.tmdb_data.get('title'), self.tmdb_data.get('year'), self._on_imdb_data)
        # --- DODATO ZA REŽISERA I TEKSTUALNU LISTU ---
        director_name = self.tmdb_data.get("director", "")
        self["director_name"].setText(director_name)

        director_img_path = self.tmdb_data.get("director_profile_path")
        if director_img_path:
            url = f"https://image.tmdb.org/t/p/w185{director_img_path}"
            filename = f"director_{director_img_path.split('/')[-1]}"

            def cb_dir(path):
                if path:
                    px = _load_pixmap_safe(path)
                    if px and self["director_img"].instance:
                        self["director_img"].instance.setPixmap(px)
                        self["director_img"].show()

            _download_image_async(url, filename, cb_dir)

        # Tekstualna lista glumaca
        cast_list = self.tmdb_data.get("cast_data", [])
        if cast_list:
            cast_names = [actor.get("name", "") for actor in cast_list]
            cast_text = "CAST:\n\n" + "\n".join(cast_names)
            self["cast_text"].setText(cast_text)
        # ---------------------------------------------
        
        # 2. Poster glavnog filma
        poster_path = self.tmdb_data.get("poster_path")
        if poster_path and os.path.exists(poster_path):
            px = _load_pixmap_safe(poster_path)
            if px and self["poster"].instance:
                self["poster"].instance.setPixmap(px)
                self["poster"].show()

        # 3. Učitavamo slike glumaca (ako ih ima u podacima)
        cast_list = self.tmdb_data.get("cast_data", [])
        self["cast_header"].setText("Cast (TMDB):")
        
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

        # 4. Prevod opisa (opciono, ako je uključen u configu)
        if config.plugins.ciefpsfiles.groq_plot_translation.value:
            self["plot"].setText(f"Plot:\n{plot}\n\n(Translating...)")
            translate_text_async(plot, self._on_translated_plot)

    def _on_translated_plot(self, success, translated_text):
        def _update_ui():
            if success:
                try:
                    lang = config.plugins.ciefpsfiles.translate_language.value.upper()
                except Exception:
                    lang = "PREVOD"
                self["plot"].setText(f"Plot ({lang}):\n{translated_text}")
            else:
                self["plot"].setText(f"Plot:\n{self.tmdb_data.get('plot', '-')}")
        self._trans_timer = eTimer()
        self._trans_timer.callback.append(_update_ui)
        self._trans_timer.start(10, True)

    def _on_imdb_data(self, success, rating):
        def _update_ui():
            if success:
                self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
            else:
                self["imdb_rating"].setText("IMDB: N/A")

        self._imdb_ui_timer = eTimer()
        self._imdb_ui_timer.callback.append(_update_ui)
        self._imdb_ui_timer.start(10, True)

    def play_movie(self):
        stream_id = self.stream_data.get("stream_id")
        title = self.stream_data.get("name", "Unknown")
        ext = self.stream_data.get("container_extension", "mp4")
        
        try:
            url = self.api.build_movie_url(stream_id, ext)
        except Exception as error:
            self["status"].setText("Movie link error: {}".format(error))
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
        self["status"].setText("Returned to details.")
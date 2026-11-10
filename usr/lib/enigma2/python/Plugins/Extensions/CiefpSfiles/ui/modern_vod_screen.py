# -*- coding: utf-8 -*-
#
# modern_vod_screen.py - Moderni VOD ekran sa backdrop-om i horizontalnom listom
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
from Screens.VirtualKeyBoard import VirtualKeyBoard
from enigma import eTimer, eServiceReference, eLabel, ePoint, loadPNG
from Tools.LoadPixmap import LoadPixmap

from .modern_vod_details import ModernVODDetailsScreen
from ..core.stalker_api import StalkerAPI
from ..core.metadata import fetch_metadata_async, fetch_omdb_rating_async, translate_text_async
from ..core.config import config
from ..core.paths import POSTERS_CACHE_DIR
from ..core.title_clean import clean_title

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

class ModernVODScreen(Screen):
    skin = """
        <screen name="CiefpSfilesModernVOD" position="0,0" size="1920,1080"
                backgroundColor="#000000">

            <!-- BACKDROP (Pozadina preko celog ekrana uz skaliranje) -->
            <widget name="backdrop" position="0,0" size="1920,1080" alphatest="blend" scale="1" zPosition="1"/>
            <!-- OKVIR ZA SELEKTOVANI POSTER -->
            <widget name="selection_frame"
                position="50,700"
                size="176,256"
                zPosition="10"
                alphatest="on"/>
            <!-- GLAVNI NASLOV FILMA -->
            <widget name="movie_title" position="50,80" size="1800,70" font="Bold;50"
                    foregroundColor="#FFFFFF" backgroundColor="#00000000" transparent="1" zPosition="3"/>

            <!-- INFO PANEL -->
            <widget name="rating" position="50,190" size="300,40" font="Bold;28"
                    foregroundColor="#00FF00" backgroundColor="#40000000" transparent="1" zPosition="3"/>
            
            <widget name="imdb_rating" position="400,190" size="300,40" font="Bold;28"
                    foregroundColor="#FFFF00" backgroundColor="#40000000" transparent="1" zPosition="3"/>

            <widget name="genres" position="50,240" size="1000,35" font="Bold;28"
                    foregroundColor="#f79d00" backgroundColor="#40000000" transparent="1" zPosition="3"/>

            <widget name="director" position="50,285" size="1000,35" font="Bold;28"
                    foregroundColor="#f79d00" backgroundColor="#40000000" transparent="1" zPosition="3"/>

            <widget name="cast" position="50,330" size="1000,80" font="Bold;26"
                    foregroundColor="#d7f702" backgroundColor="#40000000" transparent="1" valign="top" zPosition="3"/>

            <widget name="plot" position="50,420" size="1000,200" font="Regular;26"
                    foregroundColor="#FFFFFF" backgroundColor="#40000000" transparent="1" valign="top" zPosition="3"/>

            <!-- HORIZONTALNA LISTA POSTERA (10 pozicija) -->
            <widget name="poster_0" position="50,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_1" position="230,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_2" position="410,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_3" position="590,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_4" position="770,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_5" position="950,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_6" position="1130,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_7" position="1310,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_8" position="1490,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>
            <widget name="poster_9" position="1670,700" size="160,240" alphatest="blend" scale="1" zPosition="3"/>

            <!-- PAGINACIJA -->
            <widget name="page_info" position="50,980" size="400,40" font="Regular;24"
                    foregroundColor="#00FF00" backgroundColor="#00000000" transparent="1" zPosition="3"/>

            <!-- STATUS -->
            <widget name="status" position="500,980" size="1000,40" font="Regular;24"
                    foregroundColor="#00FF00" backgroundColor="#00000000" transparent="1" halign="left" zPosition="3"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="EXIT" position="50,1015" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center" zPosition="4"/>
            
            <ePixmap pixmap="buttons/green.png" position="240,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="PLAY" position="290,1015" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center" zPosition="4"/>
            
            <ePixmap pixmap="buttons/yellow.png" position="480,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="PREV 10" position="530,1015" size="200,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#808000" halign="center" valign="center" zPosition="4"/>
            
            <ePixmap pixmap="buttons/blue.png" position="750,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="NEXT 10" position="800,1015" size="200,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#000080" halign="center" valign="center" zPosition="4"/>
            
            <ePixmap pixmap="buttons/green.png" position="1000,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="INFO:SEARCH" position="1050,1015" size="300,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#00802d" halign="center" valign="center" zPosition="4"/>  
                        
            <ePixmap pixmap="buttons/red.png" position="1350,1020" size="35,35" alphatest="blend" zPosition="4"/>
            <eLabel text="MENU:DETAIL" position="1400,1015" size="300,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800073" halign="center" valign="center" zPosition="4"/>                
        </screen>
    """

    def __init__(self, session, portal, category_id, category_name):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        self.category_id = category_id
        self.category_name = category_name
        
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])
        
        self.streams = []
        self.current_page = 0
        self.items_per_page = 10
        self.selected_index = 0

        try:
            self.player_type_vod = config.plugins.ciefpsfiles.player_type_vod.value
        except Exception:
            self.player_type_vod = "4097"
        
        # Widgets
        self["backdrop"] = Pixmap()
        self["selection_frame"] = Pixmap()
        self["movie_title"] = Label("")
        self["rating"] = Label("")
        self["imdb_rating"] = Label("")
        self["genres"] = Label("")
        self["director"] = Label("")
        self["cast"] = Label("")
        self["plot"] = Label("")
        self["page_info"] = Label("")
        self["status"] = Label("")
        
        for i in range(10):
            self["poster_%d" % i] = Pixmap()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions", "InfoActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.play_selected,
                "yellow": self.prev_page,
                "blue": self.next_page,
                "ok": self.play_selected,
                "left": self.on_left,
                "right": self.on_right,
                "up": self.on_up,
                "down": self.on_down,
                "info": self.search_content,
                "menu": self.open_details,   # <-- DODATO
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frame_path = os.path.join(plugin_dir, "icons", "frame.png")

        try:
            px = _load_pixmap_safe(frame_path)

            if px is not None and self["selection_frame"].instance:
                self["selection_frame"].instance.setPixmap(px)
                self["selection_frame"].show()
                self._update_selection_frame()
            else:
                print("[CiefpSfiles] Frame PNG nije ucitan:", frame_path)

        except Exception as e:
            print("[CiefpSfiles] Frame load error:", e)

        # Ovde ostavi i ostali postojeći kod iz on_start()
        self["status"].setText(f"Loading: {self.category_name}")
        self.load_streams()
        self._update_selection_frame()

    def load_streams(self):
        ok, data, err = self.api.get_vod_streams(self.category_id)
        if ok:
            self.streams = data
            self.current_page = 0
            self.selected_index = 0
            self.render_page()
        else:
            self["status"].setText(f"Error: {err}")

    def render_page(self):
        if not self.streams:
            return

        total_pages = (
                              len(self.streams) + self.items_per_page - 1
                      ) // self.items_per_page

        start_idx = self.current_page * self.items_per_page
        end_idx = min(
            start_idx + self.items_per_page,
            len(self.streams)
        )

        plugin_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        placeholder = os.path.join(
            plugin_dir, "icons", "placeholder.png"
        )

        for i in range(10):
            widget_name = "poster_%d" % i
            widget = self[widget_name]

            stream_idx = start_idx + i

            if stream_idx < end_idx:
                stream = self.streams[stream_idx]
                title = clean_title(stream.get("name", "Unknown"))

                # Prvo prikaži placeholder.
                px = _load_pixmap_safe(placeholder)

                if px and widget.instance:
                    widget.instance.setPixmap(px)

                widget.show()

                # Učitaj poster preko metadata.py.
                fetch_metadata_async(
                    title,
                    "movie",
                    lambda success, data, wn=widget_name:
                    self._on_poster_data(wn, success, data)
                )

            else:
                widget.hide()

        # Informacije o stranici.
        self["page_info"].setText(
            "Page {}/{} | {} items".format(
                self.current_page + 1,
                total_pages,
                len(self.streams)
            )
        )
        self._update_selection_frame()

        # Ažuriraj opis i pozadinu izabranog filma.
        self.update_info_for_selected()

    def _load_poster_for_stream(self, widget_name, stream):
        title = stream.get("name", "Unknown")

        # Sinhrono učitavamo metadata (ali to može da blokira UI)
        # Zato koristimo thread, ali sa direktnim postavljanjem na widget
        def fetch_and_set():
            try:
                # Pozivamo TMDB sinhrono
                import urllib.request
                import ssl
                import json

                api_key = config.plugins.ciefpsfiles.tmdb_api_key.value
                if not api_key:
                    return
                # Prosleđujemo originalni naslov u metadata.py
                # (metadata.py već ima savršeno čišćenje)
                if not title:
                    return


                query = urllib.parse.quote(search_title)
                url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}&language=en-US"

                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                results = data.get("results", [])
                if not results:
                    return

                result = results[0]
                tmdb_id = result.get("id")

                url_details = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}&language=en-US"
                req_details = urllib.request.Request(url_details, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_details, context=ctx, timeout=10) as resp:
                    details = json.loads(resp.read().decode("utf-8"))

                poster_path = details.get("poster_path")
                if poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                    filename = f"poster_{tmdb_id}.jpg"
                    local_path = os.path.join(POSTERS_CACHE_DIR, filename)

                    if not os.path.exists(local_path):
                        req_poster = urllib.request.Request(poster_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_poster, context=ctx, timeout=10) as resp:
                            with open(local_path, 'wb') as f:
                                f.write(resp.read())

                    # Sada postavljamo poster na widget
                    def set_ui():
                        px = _load_pixmap_safe(local_path)
                        if px and self[widget_name].instance:
                            self[widget_name].instance.setPixmap(px)
                            self[widget_name].show()

                    from enigma import eTimer
                    t = eTimer()
                    t.callback.append(set_ui)
                    t.start(10, True)
            except Exception as e:
                print(f"[CiefpSfiles] Poster fetch error: {e}")

        threading.Thread(target=fetch_and_set, daemon=True).start()

    def _on_poster_data(self, widget_name, success, data):
        if not success or not isinstance(data, dict):
            print(
                "[CiefpSfiles] Poster metadata failed: {}".format(
                    widget_name
                )
            )
            return

        poster_path = data.get("poster_path")

        print(
            "[CiefpSfiles] Poster callback: {} -> {}".format(
                widget_name, poster_path
            )
        )

        if not poster_path or not os.path.isfile(poster_path):
            print(
                "[CiefpSfiles] Poster file missing: {}".format(
                    poster_path
                )
            )
            return

        def _update_ui():
            try:
                if not self[widget_name].instance:
                    print(
                        "[CiefpSfiles] Widget not ready: {}".format(
                            widget_name
                        )
                    )
                    return

                px = _load_pixmap_safe(poster_path)

                if px is None:
                    print(
                        "[CiefpSfiles] LoadPixmap failed: {}".format(
                            poster_path
                        )
                    )
                    return

                self[widget_name].instance.setPixmap(px)
                self[widget_name].show()

                print(
                    "[CiefpSfiles] Poster displayed: {}".format(
                        widget_name
                    )
                )

            except Exception as e:
                print(
                    "[CiefpSfiles] Poster UI error {}: {}".format(
                        widget_name, e
                    )
                )

        # Sačuvaj tajmer kao atribut ekrana da ne bude uništen prerano.
        if not hasattr(self, "_poster_ui_timers"):
            self._poster_ui_timers = {}

        timer = eTimer()
        self._poster_ui_timers[widget_name] = timer

        def _run_update():
            try:
                _update_ui()
            finally:
                self._poster_ui_timers.pop(widget_name, None)

        timer.callback.append(_run_update)
        timer.start(50, True)

    def _update_selection_frame(self):
        """Pomera zeleni okvir na trenutno selektovani poster."""
        poster_positions = [
            (50, 700), (230, 700), (410, 700), (590, 700), (770, 700),
            (950, 700), (1130, 700), (1310, 700), (1490, 700), (1670, 700),
        ]

        if self.selected_index < len(poster_positions):
            x, y = poster_positions[self.selected_index]
            self["selection_frame"].instance.move(ePoint(x - 8, y - 8))

    def update_info_for_selected(self):
        start_idx = self.current_page * self.items_per_page
        stream_idx = start_idx + self.selected_index

        if stream_idx >= len(self.streams):
            return

        stream = self.streams[stream_idx]
        name = clean_title(stream.get("name", "Unknown"))  # <--- OČIŠĆENO

        self["movie_title"].setText(name)
        self["status"].setText(f"Selected: {name}")

        def _do_fetch():
            fetch_metadata_async(name, "movie", self._on_tmdb_data)

        self._tmdb_timer = eTimer()
        self._tmdb_timer.callback.append(_do_fetch)
        self._tmdb_timer.start(300, True)

    def _on_tmdb_data(self, success, data):
        def _update_ui():
            if not success or not data:
                self["plot"].setText("TMDB Metadata not found.")
                return

            self._current_tmdb_data = data  # <-- DODATO: Čuvamo podatke za Details ekran

            self["movie_title"].setText(f"{data.get('title', 'Unknown')} ({data.get('year', '')})")
            self["rating"].setText(f"TMDB: {data.get('rating', '0.0')}/10")
            self["genres"].setText(f"Genres: {data.get('genres', '-')}")
            self["director"].setText(f"Director: {data.get('director', '-')}")
            self["cast"].setText(f"Cast: {data.get('cast', '-')}")

            plot = data.get("plot", "-")
            if len(plot) > 400:
                plot = plot[:400] + "..."

            # --- DODATO ZA PREVOD ---
            if config.plugins.ciefpsfiles.groq_plot_translation.value:
                self["plot"].setText(f"Plot:\n{plot}\n\n(Translating...)")
                translate_text_async(plot, self._on_translated_plot)
            else:
                self["plot"].setText(f"Plot:\n{plot}")
            # -------------------------
            # IMDb ocena
            self["imdb_rating"].setText("IMDB: Loading...")
            fetch_omdb_rating_async(data.get('title'), data.get('year'), self._on_imdb_data)

            # Backdrop preko celog ekrana
            backdrop_path = data.get("backdrop_path")
            if backdrop_path:
                if backdrop_path.startswith("http"):
                    url = backdrop_path
                else:
                    url = f"https://image.tmdb.org/t/p/w1920{backdrop_path}"

                filename = f"backdrop_{os.path.basename(backdrop_path)}"

                def cb(path):
                    if path:
                        px = _load_pixmap_safe(path)
                        if px and self["backdrop"].instance:
                            self["backdrop"].instance.setPixmap(px)
                            self["backdrop"].show()

                _download_image_async(url, filename, cb)

        self._tmdb_ui_timer = eTimer()
        self._tmdb_ui_timer.callback.append(_update_ui)
        self._tmdb_ui_timer.start(10, True)

    def _on_imdb_data(self, success, rating):
        def _update_ui():
            try:
                # Proveravamo da li widget postoji pre nego što ga ažuriramo
                if "imdb_rating" in self:
                    if success:
                        self["imdb_rating"].setText(f"IMDB: {rating}/10 ★")
                    else:
                        self["imdb_rating"].setText("IMDB: N/A")
            except Exception as e:
                print(f"[CiefpSfiles] IMDB update error: {e}")

        self._imdb_ui_timer = eTimer()
        self._imdb_ui_timer.callback.append(_update_ui)
        self._imdb_ui_timer.start(10, True)

    def _on_translated_plot(self, success, translated_text):
        def _update_ui():
            if success:
                try:
                    lang = config.plugins.ciefpsfiles.translate_language.value.upper()
                except Exception:
                    lang = "PREVOD"
                self["plot"].setText(f"Plot ({lang}):\n{translated_text}")
            else:
                current_text = self["plot"].getText()
                if "(Translating...)" in current_text:
                    self["plot"].setText(current_text.replace("(Translating...)", f"(Prevod nije uspeo: {translated_text})"))
                else:
                    self["plot"].setText(current_text + f"\n\n(Prevod nije uspeo: {translated_text})")

        self._trans_timer = eTimer()
        self._trans_timer.callback.append(_update_ui)
        self._trans_timer.start(10, True)

    def on_left(self):
        if self.selected_index > 0:
            self.selected_index -= 1
            print("[CiefpSfiles] LEFT, index:", self.selected_index)
            self.update_info_for_selected()
            self._update_selection_frame()
        elif self.current_page > 0:
            self.prev_page()

    def on_right(self):
        start_idx = self.current_page * self.items_per_page

        if (self.selected_index < 9 and
                start_idx + self.selected_index + 1 < len(self.streams)):
            self.selected_index += 1
            print("[CiefpSfiles] RIGHT, index:", self.selected_index)
            self.update_info_for_selected()
            self._update_selection_frame()
        elif (self.current_page + 1) * self.items_per_page < len(self.streams):
            self.next_page()

    def on_up(self):
        pass

    def on_down(self):
        pass

    def next_page(self):
        total_pages = (len(self.streams) + self.items_per_page - 1) // self.items_per_page
        if self.current_page + 1 < total_pages:
            self.current_page += 1
            self.selected_index = 0
            self.render_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_index = 9
            self.render_page()

    def play_selected(self):
        start_idx = self.current_page * self.items_per_page
        stream_idx = start_idx + self.selected_index
        
        if stream_idx >= len(self.streams):
            return
            
        stream = self.streams[stream_idx]
        stream_id = stream.get("stream_id")
        title = stream.get("name", "Unknown")
        ext = stream.get("container_extension", "mp4")
        
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

    def search_content(self):
        def do_search(search_term):
            if not search_term:
                return
            search_term = search_term.lower()
            # Čuvamo originalnu listu pre filtriranja ako već nismo
            if not hasattr(self, '_original_streams'):
                self._original_streams = self.streams

            filtered = [s for s in self._original_streams if search_term in s.get("name", "").lower()]

            if not filtered:
                self.session.open(MessageBox, f"No results for: '{search_term}'", MessageBox.TYPE_INFO, timeout=3)
                # Resetujemo na original ako nema rezultata
                self.streams = self._original_streams
                self.current_page = 0
                self.selected_index = 0
                self.render_page()
                return

            self.streams = filtered
            self.current_page = 0
            self.selected_index = 0
            self.render_page()
            self["status"].setText(f"Found {len(self.streams)} results for '{search_term}'")

        self.session.openWithCallback(do_search, VirtualKeyBoard, title="Search Movies", text="")

    def _on_player_closed(self, *args):
        self["status"].setText("Returned to Modern VOD.")

    def open_details(self):
        start_idx = self.current_page * self.items_per_page
        stream_idx = start_idx + self.selected_index

        if stream_idx >= len(self.streams):
            return

        stream = self.streams[stream_idx]
        title = clean_title(stream.get("name", "Unknown")) # <--- OČIŠĆENO

        # Uzimamo trenutne TMDB podatke koje smo već preuzeli za ovaj film
        # (Moramo ih sačuvati u _on_tmdb_data)
        tmdb_data = getattr(self, '_current_tmdb_data', None)

        if not tmdb_data:
            self.session.open(MessageBox, "TMDB data not loaded yet. Please wait a moment.", MessageBox.TYPE_INFO,
                              timeout=3)
            return

        self.session.open(
            ModernVODDetailsScreen,
            self.portal,
            stream,
            tmdb_data
        )
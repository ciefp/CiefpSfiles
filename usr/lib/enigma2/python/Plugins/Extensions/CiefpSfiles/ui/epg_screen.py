# -*- coding: utf-8 -*-
#
# epg_screen.py - Rich EPG ekran za CiefpSfiles
# Nezavisan od CiefpEPGinfo plugina.
#
from __future__ import print_function
import os
import re
import time
import base64
import threading
from datetime import datetime
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from enigma import (eListboxPythonMultiContent, gFont, eTimer,
                    RT_HALIGN_LEFT, RT_VALIGN_CENTER)

from Tools.LoadPixmap import LoadPixmap

from ..core.rich_metadata import (
    tmdb_search_with_translation,
    tmdb_details,
    omdb_rating,
    download_poster_async,
    download_person_photo_async,
    tmdb_search_person,
    tmdb_person_details,
    detect_non_tmdb,
    choose_placeholder,
    is_generic_title,
    get_tmdb_key,
    get_omdb_key,
    get_language,
    PLACEHOLDER,
    PLACEHOLDER_EPG,
    PLACEHOLDER_MOVIE,
    PLACEHOLDER_SERIES,
    get_epg_placeholder,
)


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


class EPGScreen(Screen):
    skin = """
        <screen name="CiefpEPGScreen" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <!-- ===== LEVI PANEL: logo + ime + lista termina ===== -->
            <widget name="channel_logo" position="40,40" size="220,140"
                    alphatest="blend" zPosition="2"/>
            
            <widget name="day" position="500,40" size="200,40" font="Regular;30"
                    foregroundColor="#00BFFF" backgroundColor="#011a2e" transparent="1" halign="left"/>
                    
            <widget name="date" position="500,100" size="200,40" font="Regular;30"
                    foregroundColor="#00BFFF" backgroundColor="#011a2e" transparent="1" halign="left"/>

            <widget name="clock" position="290,40" size="200,100" font="Regular;80"
                    foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" halign="left"/>
        
            <widget name="channel_name" position="40,200" size="600,50"
                    font="Bold;34" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="epg_list" position="40,250" size="620,720"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;24" backgroundColor="#011a2e"/>

            <!-- ===== CENTAR: detalji termina ===== -->
            <widget name="program_title" position="700,40" size="600,80"
                    font="Bold;36" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_epg" position="700,125" size="600,35"
                    font="Regular;22" foregroundColor="#A0A0A0"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_time" position="700,170" size="400,35"
                    font="Regular;26" foregroundColor="#00FF00"
                    backgroundColor="#011a2e" transparent="1"/>
            <widget name="program_duration" position="1120,170" size="300,35"
                    font="Regular;26" foregroundColor="#D3D3D3"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_tmdb" position="700,210" size="360,35"
                    font="Regular;24" foregroundColor="#03a81f"
                    backgroundColor="#011a2e" transparent="1"/>
            <widget name="program_imdb" position="1080,210" size="360,35"
                    font="Regular;24" foregroundColor="#F5C518"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_genres" position="700,250" size="600,35"
                    font="Regular;24" foregroundColor="#f702db"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_director" position="700,290" size="600,35"
                    font="Regular;24" foregroundColor="#f79102"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="program_plot" position="700,330" size="600,396"
                    font="Regular;22" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1" valign="top"/>

            <widget name="cast_header" position="700,730" size="200,30"
                    font="Bold;24" foregroundColor="#00FFFF"
                    backgroundColor="#011a2e" transparent="1"/>
            <widget name="program_cast" position="700,760" size="720,180"
                    font="Regular;20" foregroundColor="#00FFFF"
                    backgroundColor="#011a2e" transparent="1" valign="top"/>

            <!-- ===== DESNO: poster ===== -->
            <widget name="poster" position="1400,40" size="500,750"
                    alphatest="blend" zPosition="2"/>

            <!-- ===== STATUS ===== -->
            <widget name="status" position="700,960" size="1180,40"
                    font="Regular;22" foregroundColor="#00FF00"
                    backgroundColor="#011a2e" transparent="1" halign="left"/>

            <!-- ===== DUGMAD ===== -->
            <ePixmap pixmap="buttons/red.png" position="0,1010" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1010" size="180,40" font="Bold;26"
                    foregroundColor="white" backgroundColor="#800000"
                    halign="center" valign="center"/>

            <ePixmap pixmap="buttons/green.png" position="240,1010" size="35,35" alphatest="blend"/>
            <eLabel text="FILMOGRAPHY" position="290,1010" size="200,40" font="Bold;26"
                    foregroundColor="white" backgroundColor="#008000"
                    halign="center" valign="center"/>

            <ePixmap pixmap="buttons/yellow.png" position="500,1010" size="35,35" alphatest="blend"/>
            <eLabel text="CAST" position="550,1010" size="160,40" font="Bold;26"
                    foregroundColor="white" backgroundColor="#808000"
                    halign="center" valign="center"/>

            <ePixmap pixmap="buttons/blue.png" position="720,1010" size="35,35" alphatest="blend"/>
            <eLabel text="CHANNELS" position="770,1010" size="200,40" font="Bold;26"
                    foregroundColor="white" backgroundColor="#000080"
                    halign="center" valign="center"/>

            <ePixmap pixmap="buttons/red.png" position="990,1010" size="35,35" alphatest="blend"/>
            <eLabel text="INFO:REFRESH" position="1040,1010" size="220,40" font="Bold;26"
                    foregroundColor="white" backgroundColor="#960396"
                    halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, api, stream_id, channel_name, stream_icon=None,
                 channels_list=None, current_channel_idx=0):
        Screen.__init__(self, session)
        self.session = session
        self.api = api
        self.stream_id = stream_id
        self.channel_name = channel_name
        self.stream_icon = stream_icon

        self["day"] = Label("")
        self["date"] = Label("")
        self["clock"] = Label("")
        self.channels_list = channels_list or []
        self.current_channel_idx = current_channel_idx

        self.epg_listings = []
        self.epg_events = []
        self.current_listing = None
        self.current_media_details = None
        self.current_media_type = None

        # Za filmography / cast explore
        self.current_person_details = None
        self.current_person_name = None
        self._saved_media_state = None

        # Timer-i
        self._ui_timer = None
        self._logo_timer = None
        self._poster_timer = None
        self._tmdb_in_progress = False

        # Widgets
        self["channel_logo"] = Pixmap()
        self["channel_name"] = Label(channel_name)
        self["epg_list"] = MenuList([], enableWrapAround=True,
                                    content=eListboxPythonMultiContent)
        self["epg_list"].l.setItemHeight(50)
        self["epg_list"].l.setFont(0, gFont("Regular", 24))

        self["program_title"] = Label("")
        self["program_epg"] = Label("")
        self["program_time"] = Label("")
        self["program_duration"] = Label("")
        self["program_tmdb"] = Label("")
        self["program_imdb"] = Label("")
        self["program_genres"] = Label("")
        self["program_director"] = Label("")
        self["program_plot"] = Label("")
        self["cast_header"] = Label("")
        self["program_cast"] = Label("")
        self["poster"] = Pixmap()
        self["status"] = Label("Loading EPG...")

        # Akcije
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "InfoActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.filmography_browser,   # ← ažurirano
                "yellow": self.cast_explore,          # ← ažurirano
                "blue": self.open_channels,
                "info": self.refresh_epg,
                "ok": self.on_ok,
                "up": self.on_up,
                "down": self.on_down,
            }, -1
        )

        if stream_icon:
            self._load_channel_logo(stream_icon)
        else:
            self._set_default_logo()

        self._set_poster(PLACEHOLDER_EPG)
        self.onLayoutFinish.append(self.on_start)

    def close(self):
        try:
            if hasattr(self, "_clock_timer") and self._clock_timer:
                self._clock_timer.stop()
        except Exception:
            pass
        Screen.close(self)

    def on_start(self):
        self._update_clock()
        self._clock_timer = eTimer()
        self._clock_timer.callback.append(self._update_clock)
        self._clock_timer.start(1000)
        threading.Thread(target=self._fetch_full_epg, daemon=True).start()

    def _update_clock(self):
        try:
            now = datetime.now()
            days = ["Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday"]
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            self["day"].setText(days[now.weekday()])
            self["date"].setText("%d. %s" % (now.day, months[now.month - 1]))
            self["clock"].setText(now.strftime("%H:%M"))
        except Exception as e:
            print("[EPGScreen] clock update error:", e)

    # ---------- LOGO KANALA ----------
    def _set_default_logo(self):
        icon = _get_icon_path("icon_live.png")
        px = _load_pixmap_safe(icon)
        if px and self["channel_logo"].instance:
            self["channel_logo"].instance.setPixmap(px)

    def _load_channel_logo(self, url):
        if not url or not url.startswith("http"):
            self._set_default_logo()
            return

        def worker():
            try:
                from ..core.rich_metadata import download_image_sync
                import hashlib
                h = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
                ext = ".png"
                if ".jpg" in url.lower() or ".jpeg" in url.lower():
                    ext = ".jpg"
                fname = "channel_logo_%s%s" % (h, ext)
                path = download_image_sync(url, fname)
                if path:
                    self._apply_logo(path)
                else:
                    self._set_default_logo()
            except Exception as e:
                print("[EPGScreen] logo download error:", e)
                self._set_default_logo()

        threading.Thread(target=worker, daemon=True).start()

    def _apply_logo(self, path):
        px = _load_pixmap_safe(path)
        if px and self["channel_logo"].instance:
            self["channel_logo"].instance.setPixmap(px)

    # ---------- EPG FETCH ----------
    def _fetch_full_epg(self):
        try:
            ok, data, error = self.api.get_short_epg(self.stream_id, limit=100)
            if not ok:
                raise RuntimeError(error or "EPG request failed")

            listings = data.get("epg_listings", [])
            events = []
            now = int(time.time())

            for listing in listings:
                try:
                    start_ts = int(listing.get("start_timestamp")
                                   or listing.get("start") or 0)
                    stop_ts = int(listing.get("stop_timestamp")
                                  or listing.get("end") or 0)

                    if stop_ts < now:
                        continue

                    try:
                        enc_title = listing.get("title", "")
                        title = (base64.b64decode(enc_title)
                                 .decode("utf-8", errors="ignore")
                                 if enc_title else "")
                    except Exception:
                        title = listing.get("title", "")

                    try:
                        enc_desc = listing.get("description", "")
                        desc = (base64.b64decode(enc_desc)
                                .decode("utf-8", errors="ignore")
                                if enc_desc else "")
                    except Exception:
                        desc = listing.get("description", "")

                    events.append({
                        "start": start_ts,
                        "stop": stop_ts,
                        "title": title,
                        "desc": desc,
                    })
                except Exception as e:
                    print("[EPGScreen] Error parsing listing:", e)

            self.epg_events = events

            self._ui_timer = eTimer()
            self._ui_timer.callback.append(self._build_epg_list_ui)
            self._ui_timer.start(10, True)

        except Exception as e:
            print("[EPGScreen] Fetch error:", e)
            self._safe_status("EPG fetch error: %s" % e)

    def _safe_status(self, text):
        def _do():
            self["status"].setText(text)
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)
        self._status_timer = t

    def _build_epg_list_ui(self):
        if not self.epg_events:
            self["epg_list"].setList([
                [("No EPG data available for this channel.", "")],
            ])
            self["status"].setText("No EPG data")
            self["program_title"].setText(self.channel_name)
            self["program_plot"].setText("No EPG data available.")
            return

        items = []
        self._list_index_to_event = {}
        last_date = None
        list_idx = 0
        now = int(time.time())

        for idx, ev in enumerate(self.epg_events):
            start_ts = ev["start"]
            stop_ts = ev["stop"]
            title = ev["title"]

            try:
                current_date = time.strftime("%d.%m.%Y", time.localtime(start_ts)) if start_ts else "--.--.----"
                start_time = time.strftime("%H:%M", time.localtime(start_ts)) if start_ts else "--:--"
                end_time = time.strftime("%H:%M", time.localtime(stop_ts)) if stop_ts else "--:--"
            except Exception:
                current_date = "--.--.----"
                start_time = "--:--"
                end_time = "--:--"

            if current_date != last_date:
                last_date = current_date
                sep_text = "────────── %s ──────────" % current_date
                items.append([
                    ("sep_%d" % list_idx, ""),
                    MultiContentEntryText(
                        pos=(0, 0), size=(600, 50), font=0,
                        flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                        text=sep_text),
                ])
                list_idx += 1

            is_current = (start_ts <= now < stop_ts)
            prefix = "▶" if is_current else "  "
            display = "%s %s - %s  %s" % (prefix, start_time, end_time, title)

            items.append([
                ("evt_%d" % idx, ""),
                MultiContentEntryText(
                    pos=(0, 0), size=(600, 50), font=0,
                    flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                    text=display),
            ])
            self._list_index_to_event[list_idx] = ev
            list_idx += 1

        self["epg_list"].setList(items)
        first_evt_idx = 0
        for i in range(len(items)):
            if i in self._list_index_to_event:
                first_evt_idx = i
                break
        self["epg_list"].moveToIndex(first_evt_idx)
        self["status"].setText("%d EPG entries loaded" % len(self.epg_events))

        self._on_selection_changed()

    def _on_selection_changed(self):
        try:
            idx = self["epg_list"].getSelectedIndex()
        except Exception:
            return

        mapping = getattr(self, "_list_index_to_event", {})
        selected = mapping.get(idx)

        if not selected:
            for i in range(idx, len(self.epg_events) + 20):
                if i in mapping:
                    try:
                        self["epg_list"].moveToIndex(i)
                    except Exception:
                        pass
                    selected = mapping[i]
                    break
            if not selected:
                return

        self.current_listing = selected
        self._show_program_details(selected)

    def on_up(self):
        try:
            self["epg_list"].up()
            self._on_selection_changed()
        except Exception:
            pass

    def on_down(self):
        try:
            self["epg_list"].down()
            self._on_selection_changed()
        except Exception:
            pass

    def on_ok(self):
        self._on_selection_changed()

    # ---------- DETALJI TERMINA ----------
    def _show_program_details(self, ev):
        title = ev["title"]
        desc = ev["desc"]
        start_ts = ev["start"]
        stop_ts = ev["stop"]

        self["program_title"].setText(title or "Unknown")
        self["program_epg"].setText("EPG: %s" % title if title else "")

        if start_ts and stop_ts:
            try:
                st = time.strftime("%H:%M", time.localtime(start_ts))
                et = time.strftime("%H:%M", time.localtime(stop_ts))
                self["program_time"].setText("%s - %s" % (st, et))
                minutes = (stop_ts - start_ts) // 60
                self["program_duration"].setText("%d min" % minutes)
            except Exception:
                self["program_time"].setText("")
                self["program_duration"].setText("")
        else:
            self["program_time"].setText("")
            self["program_duration"].setText("")

        self["program_tmdb"].setText("")
        self["program_imdb"].setText("")
        self["program_genres"].setText("")
        self["program_director"].setText("")
        self["cast_header"].setText("")
        self["program_cast"].setText("")
        self.current_media_details = None
        self.current_media_type = None

        if desc:
            plot = desc[:750]
            if len(desc) > 750:
                cut = desc[:750].rfind(". ")
                if cut > 400:
                    plot = desc[:cut + 1] + " ..."
                else:
                    plot = desc[:750] + " ..."
            self["program_plot"].setText("Plot:\n%s" % plot)
        else:
            self["program_plot"].setText("Plot:\nNo description available.")

        if is_generic_title(title):
            self["status"].setText("Non-TMDB content (EPG only)")
            non_tmdb, placeholder = detect_non_tmdb(title, desc, epg=True)
            if non_tmdb:
                self._set_poster(placeholder)
            else:
                self._set_poster(PLACEHOLDER_EPG)
            return

        api_key = get_tmdb_key()
        if not api_key:
            self["status"].setText("TMDB API key not set")
            non_tmdb, placeholder = detect_non_tmdb(title, desc, epg=True)
            self._set_poster(placeholder or PLACEHOLDER_EPG)
            return

        if self._tmdb_in_progress:
            return
        self._tmdb_in_progress = True
        self["status"].setText("Searching TMDB: %s" % title)

        search_title = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()
        if not search_title:
            search_title = title

        year = None
        m = re.search(r"\b(19|20)\d{2}\b", title + " " + desc)
        if m:
            year = int(m.group(0))

        threading.Thread(
            target=self._fetch_tmdb_async,
            args=(search_title, year, desc),
            daemon=True
        ).start()

    def _fetch_tmdb_async(self, title, year, epg_description):
        try:
            api_key = get_tmdb_key()
            if not api_key:
                self._tmdb_fallback(epg_description, "TMDB key missing")
                return

            lang = get_language()
            result, media_type = tmdb_search_with_translation(
                title, year, api_key, lang)

            if not result:
                self._tmdb_fallback(epg_description, "Not found on TMDB")
                return

            media_id = result.get("id")
            details = tmdb_details(media_id, media_type, api_key, lang)

            if not details:
                print("[EPGScreen] Details failed, using search result fallback for:", title)
                details = result.copy()
                details["credits"] = {"cast": [], "crew": []}
                details["genres"] = []
                details["overview"] = result.get("overview", epg_description)

            self.current_media_details = details
            self.current_media_type = media_type

            self._tmdb_ui_timer = eTimer()
            self._tmdb_ui_timer.callback.append(
                lambda: self._update_ui_with_tmdb(details, media_type))
            self._tmdb_ui_timer.start(10, True)

        except Exception as e:
            print("[EPGScreen] TMDB async error:", e)
            self._tmdb_fallback(epg_description, "TMDB error")
        finally:
            self._tmdb_in_progress = False

    def _tmdb_fallback(self, epg_description, reason):
        def _do():
            self["status"].setText("%s - EPG only" % reason)
            try:
                title_text = self["program_title"].getText() or ""
            except Exception:
                title_text = ""
            non_tmdb, placeholder = detect_non_tmdb(
                title_text, epg_description or "",
                epg=True)
            if non_tmdb:
                self._set_poster(placeholder)
            else:
                self._set_poster(PLACEHOLDER_EPG)
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)
        self._fallback_timer = t

    def _update_ui_with_tmdb(self, details, media_type):
        title = details.get("title") if media_type == "movie" else details.get("name", "")
        year = ((details.get("release_date") or "")[:4]
                if media_type == "movie"
                else (details.get("first_air_date") or "")[:4])

        self["program_title"].setText(
            "%s%s" % (title, (" (%s)" % year) if year else ""))

        vote = details.get("vote_average", 0)
        if vote:
            self["program_tmdb"].setText("TMDB: %.1f/10 ★" % vote)
        else:
            self["program_tmdb"].setText("TMDB: N/A")

        genres = [g.get("name", "") for g in details.get("genres", [])]
        self["program_genres"].setText(
            "Genres: %s" % (", ".join(genres) if genres else "N/A"))

        credits = details.get("credits", {})
        crew = credits.get("crew", [])
        directors = [c.get("name", "") for c in crew
                     if c.get("job") == "Director"]
        if media_type == "tv":
            creators = [c.get("name", "")
                        for c in details.get("created_by", [])]
            if creators:
                self["program_director"].setText(
                    "Created by: %s" % ", ".join(creators[:3]))
            elif directors:
                self["program_director"].setText(
                    "Director: %s" % ", ".join(directors[:3]))
            else:
                self["program_director"].setText("")
        else:
            if directors:
                self["program_director"].setText(
                    "Director: %s" % ", ".join(directors[:3]))
            else:
                self["program_director"].setText("")

        overview = (details.get("overview") or "").strip()
        if overview:
            plot = overview[:750]
            if len(overview) > 750:
                cut = overview[:750].rfind(". ")
                if cut > 400:
                    plot = overview[:cut + 1] + " ..."
                else:
                    plot = overview[:750] + " ..."
            self["program_plot"].setText("Plot:\n%s" % plot)

        cast = credits.get("cast", [])[:10]
        if cast:
            self["cast_header"].setText("Cast:")
            rows = []
            for a in cast:
                name = a.get("name", "").strip()
                char = a.get("character", "").strip()
                if len(char) > 30:
                    char = char[:30] + "…"
                if char:
                    rows.append("• %s as %s" % (name, char))
                else:
                    rows.append("• %s" % name)
            self["program_cast"].setText("\n".join(rows))
        else:
            self["cast_header"].setText("")
            self["program_cast"].setText("")

        poster_path = details.get("poster_path")
        media_id = details.get("id")
        if poster_path and media_id:
            self._download_poster(poster_path, media_id, media_type)
        else:
            genres_list = [g.get("name", "") for g in details.get("genres", [])]
            placeholder = choose_placeholder(genres_list, epg=True)
            if placeholder == PLACEHOLDER_EPG:
                if media_type == "movie":
                    placeholder = (PLACEHOLDER_MOVIE
                                   if os.path.exists(PLACEHOLDER_MOVIE)
                                   else PLACEHOLDER_EPG)
                elif media_type == "tv":
                    placeholder = (PLACEHOLDER_SERIES
                                   if os.path.exists(PLACEHOLDER_SERIES)
                                   else PLACEHOLDER_EPG)
            self._set_poster(placeholder)

        omdb_key = get_omdb_key()
        if omdb_key:
            self["program_imdb"].setText("IMDB: Loading...")
            threading.Thread(
                target=self._fetch_imdb_async,
                args=(details, media_type),
                daemon=True
            ).start()
        else:
            self["program_imdb"].setText("")

        self["status"].setText("TMDB info loaded")

    def _fetch_imdb_async(self, details, media_type):
        try:
            omdb_key = get_omdb_key()
            rating = omdb_rating(details, media_type, omdb_key)
            def _do():
                if rating:
                    self["program_imdb"].setText("IMDB: %s/10 ★" % rating)
                else:
                    self["program_imdb"].setText("IMDB: N/A")
            t = eTimer()
            t.callback.append(_do)
            t.start(10, True)
            self._imdb_timer = t
        except Exception as e:
            print("[EPGScreen] IMDB error:", e)

    # ---------- POSTER ----------
    def _download_poster(self, poster_path, media_id, media_type):
        def cb(path):
            def _do():
                if path:
                    self._set_poster(path)
                else:
                    self._set_poster(PLACEHOLDER_EPG)
            t = eTimer()
            t.callback.append(_do)
            t.start(10, True)
            self._poster_timer = t

        download_poster_async(poster_path, media_id, media_type, cb)

    def _set_poster(self, path):
        px = _load_pixmap_safe(path)
        if px and self["poster"].instance:
            try:
                self["poster"].instance.setPixmap(px)
                self["poster"].show()
                return
            except Exception:
                pass
        epg_ph = get_epg_placeholder()
        px = _load_pixmap_safe(epg_ph)
        if px and self["poster"].instance:
            try:
                self["poster"].instance.setPixmap(px)
                self["poster"].show()
            except Exception:
                pass

    # ==========================================================
    #  NOVO: FILMOGRAPHY (zeleno dugme)
    # ==========================================================
    def filmography_browser(self):
        # Ako je već učitan profil osobe, otvori filmografiju direktno
        if self.current_person_details:
            self._show_person_filmography_choicebox()
            return

        if not self.current_media_details:
            self.session.open(
                MessageBox,
                "No TMDB info loaded.\nSelect a movie/series with TMDB data first.",
                MessageBox.TYPE_INFO, timeout=3)
            return

        credits = self.current_media_details.get("credits", {})
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])
        directors = [c for c in crew if c.get("job") == "Director"]

        menu = []
        if directors:
            for d in directors[:3]:
                menu.append(("Director: %s" % d.get("name", ""), d))
        for i, a in enumerate(cast[:25]):
            name = a.get("name", "")
            char = a.get("character", "")
            if len(char) > 30:
                char = char[:30] + "…"
            if char:
                menu.append(("%d. %s (%s)" % (i + 1, name, char), a))
            else:
                menu.append(("%d. %s" % (i + 1, name), a))

        if not menu:
            self.session.open(
                MessageBox,
                "No cast/director info available.",
                MessageBox.TYPE_INFO, timeout=3)
            return

        def person_selected(choice):
            if not choice or not choice[1]:
                return
            person = choice[1]
            name = person.get("name", "")
            if not name:
                return
            self["status"].setText("Loading filmography: %s..." % name)
            threading.Thread(
                target=self._load_person_for_filmography,
                args=(name,),
                daemon=True
            ).start()

        title = (self.current_media_details.get("title")
                 or self.current_media_details.get("name", ""))
        self.session.openWithCallback(
            person_selected, ChoiceBox,
            title="Filmography Browser: %s" % title,
            list=menu
        )

    def _load_person_for_filmography(self, name):
        api_key = get_tmdb_key()
        if not api_key:
            self._safe_status("TMDB API key not set")
            return
        result = tmdb_search_person(name, api_key, get_language())
        if not result:
            self._safe_status("Person not found: %s" % name)
            return
        person_id = result.get("id")
        details = tmdb_person_details(person_id, api_key, get_language())
        if not details:
            self._safe_status("Person details error: %s" % name)
            return
        self.current_person_details = details
        self.current_person_name = details.get("name", name)

        def _do():
            self._show_person_filmography_choicebox()
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)
        self._person_timer = t

    def _show_person_filmography_choicebox(self):
        if not self.current_person_details:
            self._safe_status("No person loaded")
            return

        person = self.current_person_details
        person_name = person.get("name", "Unknown")
        movie_credits = person.get("movie_credits", {}).get("cast", [])
        tv_credits = person.get("tv_credits", {}).get("cast", [])

        seen_m = set()
        unique_movies = []
        for m in movie_credits:
            if m.get("id") not in seen_m:
                seen_m.add(m.get("id"))
                unique_movies.append(m)

        seen_t = set()
        unique_tv = []
        for t in tv_credits:
            if t.get("id") not in seen_t:
                seen_t.add(t.get("id"))
                unique_tv.append(t)

        def score(x):
            pop = x.get("popularity", 0) or 0
            votes = x.get("vote_count", 0) or 0
            return votes * 10 + pop

        unique_movies.sort(key=score, reverse=True)
        unique_tv.sort(key=score, reverse=True)
        top_movies = unique_movies[:10]
        top_tv = unique_tv[:10]

        menu = []
        if top_movies:
            menu.append(("── MOVIES (%d) ──" % len(top_movies), None))
            for m in top_movies:
                title = m.get("title", "N/A")
                year = (m.get("release_date") or "")[:4]
                rating = m.get("vote_average", 0) or 0
                year_str = " (%s)" % year if year else ""
                rating_str = " ★%.1f" % rating if rating > 0 else ""
                menu.append(("• %s%s%s" % (title, year_str, rating_str),
                             ("movie", m)))
        if top_tv:
            menu.append(("── TV SERIES (%d) ──" % len(top_tv), None))
            for t in top_tv:
                name = t.get("name", "N/A")
                year = (t.get("first_air_date") or "")[:4]
                rating = t.get("vote_average", 0) or 0
                year_str = " (%s)" % year if year else ""
                rating_str = " ★%.1f" % rating if rating > 0 else ""
                menu.append(("• %s%s%s" % (name, year_str, rating_str),
                             ("tv", t)))

        if not menu:
            self._safe_status("No filmography for %s" % person_name)
            return

        def media_selected(choice):
            if not choice or choice[1] is None:
                return
            media_type, media_data = choice[1]
            media_id = media_data.get("id")
            title = media_data.get("title") or media_data.get("name", "Unknown")
            if media_id:
                self["status"].setText("Loading %s..." % title)
                threading.Thread(
                    target=self._load_media_from_filmography,
                    args=(media_id, media_type, title),
                    daemon=True
                ).start()

        self.session.openWithCallback(
            media_selected, ChoiceBox,
            title="Filmography: %s" % person_name,
            list=menu
        )

    def _load_media_from_filmography(self, media_id, media_type, media_title):
        api_key = get_tmdb_key()
        if not api_key:
            self._safe_status("TMDB API key not set")
            return
        try:
            details = tmdb_details(media_id, media_type, api_key, get_language())
            if not details:
                self._safe_status("Error loading media details")
                return
            if not self._saved_media_state:
                self._saved_media_state = {
                    "media_details": self.current_media_details,
                    "media_type": self.current_media_type,
                }
            self.current_media_details = details
            self.current_media_type = media_type

            def _do():
                self._update_ui_with_tmdb(details, media_type)
                person_name = getattr(self, "current_person_name", "")
                if person_name:
                    self["program_epg"].setText("From filmography: %s" % person_name)
                self["status"].setText("Loaded: %s" % media_title)
            t = eTimer()
            t.callback.append(_do)
            t.start(10, True)
            self._filmography_ui_timer = t
        except Exception as e:
            print("[EPGScreen] load media from filmography error:", e)
            self._safe_status("Error loading media")

    # ==========================================================
    #  NOVO: CAST EXPLORE (žuto dugme)
    # ==========================================================
    def cast_explore(self):
        if not self.current_media_details:
            self.session.open(
                MessageBox,
                "No TMDB info loaded.\nSelect a movie/series with TMDB data first.",
                MessageBox.TYPE_INFO, timeout=3)
            return

        credits = self.current_media_details.get("credits", {})
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])
        directors = [c for c in crew if c.get("job") == "Director"]

        menu = []
        if directors:
            for d in directors[:2]:
                menu.append(("Director: %s" % d.get("name", ""), d))
        for i, a in enumerate(cast[:20]):
            name = a.get("name", "")
            char = a.get("character", "")
            if len(char) > 30:
                char = char[:30] + "…"
            menu.append(("%d. %s (%s)" % (i + 1, name, char), a))

        if not menu:
            self.session.open(
                MessageBox,
                "No cast info available.",
                MessageBox.TYPE_INFO, timeout=3)
            return

        def cb(choice):
            if not choice or not choice[1]:
                return
            person = choice[1]
            name = person.get("name", "")
            if name:
                self["status"].setText("Loading: %s..." % name)
                threading.Thread(
                    target=self._load_person_async,
                    args=(name,),
                    daemon=True
                ).start()

        title = (self.current_media_details.get("title")
                 or self.current_media_details.get("name", ""))
        self.session.openWithCallback(
            cb, ChoiceBox,
            title="Cast & Crew: %s" % title,
            list=menu
        )

    def _load_person_async(self, name):
        api_key = get_tmdb_key()
        if not api_key:
            self._safe_status("TMDB API key not set")
            return
        result = tmdb_search_person(name, api_key, get_language())
        if not result:
            self._safe_status("Person not found: %s" % name)
            return
        person_id = result.get("id")
        details = tmdb_person_details(person_id, api_key, get_language())
        if not details:
            self._safe_status("Person details error: %s" % name)
            return
        self._saved_media_state = {
            "media_details": self.current_media_details,
            "media_type": self.current_media_type,
        }
        self.current_person_details = details

        def _do():
            self._display_person_info(details)
        t = eTimer()
        t.callback.append(_do)
        t.start(10, True)
        self._person_info_timer = t

    def _display_person_info(self, details):
        person_id = details.get("id")
        name = details.get("name", "N/A")
        known_for = details.get("known_for_department", "")
        birthday = details.get("birthday", "")
        deathday = details.get("deathday", "")
        place_of_birth = details.get("place_of_birth", "")
        biography = details.get("biography", "").strip()

        movie_credits = details.get("movie_credits", {}).get("cast", [])
        tv_credits = details.get("tv_credits", {}).get("cast", [])

        movie_ids = set()
        unique_movies = []
        for m in movie_credits:
            if m.get("id") not in movie_ids:
                movie_ids.add(m.get("id"))
                unique_movies.append(m)
        tv_ids = set()
        unique_tv = []
        for t in tv_credits:
            if t.get("id") not in tv_ids:
                tv_ids.add(t.get("id"))
                unique_tv.append(t)

        movie_count = len(unique_movies)
        tv_count = len(unique_tv)

        self["program_title"].setText(name + (("  (%s)" % known_for) if known_for else ""))
        self["program_epg"].setText("Actor Profile")

        if birthday:
            try:
                y, m, d = birthday.split("-")
                pretty_birth = "%02d.%02d.%s" % (int(d), int(m), y)
            except Exception:
                pretty_birth = birthday
        else:
            pretty_birth = "N/A"

        self["program_time"].setText("Born: %s" % pretty_birth)
        self["program_duration"].setText("Place: %s" % place_of_birth if place_of_birth else "")
        self["program_tmdb"].setText("Movies: %d" % movie_count)
        self["program_imdb"].setText("TV Series: %d" % tv_count)

        if deathday:
            try:
                y, m, d = deathday.split("-")
                pretty_death = "%02d.%02d.%s" % (int(d), int(m), y)
            except Exception:
                pretty_death = deathday
            self["program_genres"].setText("Died: %s" % pretty_death)
        else:
            self["program_genres"].setText("")

        self["program_director"].setText("")

        if biography:
            biography = re.sub(r"\n{2,}", "\n", biography).strip()
            MAX_BIO = 700
            if len(biography) > MAX_BIO:
                cut = biography[:MAX_BIO].rfind(". ")
                if cut > 400:
                    biography = biography[:cut + 1] + " ..."
                else:
                    cut = biography[:MAX_BIO].rfind(" ")
                    if cut > 400:
                        biography = biography[:cut] + " ..."
                    else:
                        biography = biography[:MAX_BIO] + " ..."
            self["program_plot"].setText("Biography:\n%s" % biography)

        self["cast_header"].setText("Known For:")

        def movie_score(m):
            pop = m.get("popularity", 0) or 0
            votes = m.get("vote_count", 0) or 0
            return votes * 10 + pop

        def tv_score(t):
            pop = t.get("popularity", 0) or 0
            votes = t.get("vote_count", 0) or 0
            return votes * 10 + pop

        unique_movies.sort(key=movie_score, reverse=True)
        unique_tv.sort(key=tv_score, reverse=True)
        top_movies = unique_movies[:5]
        top_tv = unique_tv[:5]

        def fmt_movie(m):
            title = m.get("title", "N/A")
            year = (m.get("release_date") or "")[:4]
            rating = m.get("vote_average", 0) or 0
            year_str = " (%s)" % year if year else ""
            rating_str = " %.1f★" % rating if rating > 0 else ""
            return "• %s%s%s" % (title, year_str, rating_str)

        def fmt_tv(t):
            name = t.get("name", "N/A")
            year = (t.get("first_air_date") or "")[:4]
            rating = t.get("vote_average", 0) or 0
            year_str = " (%s)" % year if year else ""
            rating_str = " %.1f★" % rating if rating > 0 else ""
            return "• %s%s%s" % (name, year_str, rating_str)

        col1_text = "\n".join([fmt_movie(m) for m in top_movies]) if top_movies else "No movies"
        col2_text = "\n".join([fmt_tv(t) for t in top_tv]) if top_tv else "No TV series"
        col1_text = "Movies:\n" + col1_text
        col2_text = "TV Series:\n" + col2_text
        self["program_cast"].setText(col1_text + "\n\n" + col2_text)

        profile_path = details.get("profile_path")
        if profile_path:
            self._download_person_photo(profile_path, person_id)
        else:
            self._set_poster(PLACEHOLDER_EPG)

        self["status"].setText("Profile: %s  (BACK to return)" % name)

    def _download_person_photo(self, profile_path, person_id):
        def cb(path):
            def _do():
                if path:
                    self._set_poster(path)
                else:
                    self._set_poster(PLACEHOLDER_EPG)
            t = eTimer()
            t.callback.append(_do)
            t.start(10, True)
            self._photo_timer = t

        download_person_photo_async(profile_path, person_id, cb)

    # ---------- CHANNELS (plavo dugme) ----------
    def open_channels(self):
        if not self.channels_list:
            self.session.open(
                MessageBox,
                "Channel list not available.\n"
                "Open EPG from Live TV list to enable channel switching.",
                MessageBox.TYPE_INFO, timeout=4)
            return

        menu = []
        for i, ch in enumerate(self.channels_list):
            name = ch.get("name", "Unknown")
            prefix = "▶ " if i == self.current_channel_idx else "   "
            menu.append((prefix + name, i))

        def cb(choice):
            if not choice:
                return
            idx = choice[1]
            if not (0 <= idx < len(self.channels_list)):
                return
            self._switch_channel(idx)

        self.session.openWithCallback(
            cb, ChoiceBox,
            title="Switch Channel",
            list=menu
        )

    def _switch_channel(self, new_idx):
        if not (0 <= new_idx < len(self.channels_list)):
            return
        new_ch = self.channels_list[new_idx]
        new_stream_id = new_ch.get("stream_id")
        new_name = new_ch.get("name", "Unknown")
        new_icon = new_ch.get("stream_icon")

        if not new_stream_id:
            self["status"].setText("Invalid stream id")
            return

        self.stream_id = new_stream_id
        self.channel_name = new_name
        self.stream_icon = new_icon
        self.current_channel_idx = new_idx
        self.epg_events = []
        self.current_listing = None
        self.current_media_details = None
        self.current_media_type = None
        self._tmdb_in_progress = False
        self.current_person_details = None
        self.current_person_name = None
        self._saved_media_state = None

        self["channel_name"].setText(new_name)
        self["program_title"].setText(new_name)
        self["program_epg"].setText("")
        self["program_time"].setText("")
        self["program_duration"].setText("")
        self["program_tmdb"].setText("")
        self["program_imdb"].setText("")
        self["program_genres"].setText("")
        self["program_director"].setText("")
        self["program_plot"].setText("Loading EPG...")
        self["cast_header"].setText("")
        self["program_cast"].setText("")
        self._set_poster(PLACEHOLDER_EPG)
        self["status"].setText("Loading EPG for %s..." % new_name)

        if new_icon:
            self._load_channel_logo(new_icon)
        else:
            self._set_default_logo()

        threading.Thread(target=self._fetch_full_epg, daemon=True).start()

    def refresh_epg(self):
        self["status"].setText("Refreshing EPG...")
        self.current_person_details = None
        self.current_person_name = None
        self._saved_media_state = None
        threading.Thread(target=self._fetch_full_epg, daemon=True).start()

    def close(self):
        try:
            if hasattr(self, "_clock_timer") and self._clock_timer:
                self._clock_timer.stop()
        except Exception:
            pass
        Screen.close(self)
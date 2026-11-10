# -*- coding: utf-8 -*-
import os
import shutil
import threading
import requests
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from ..core.config import config

from ..core.paths import (
    TMDB_KEY_FILE, OMDB_KEY_FILE, GROQ_KEY_FILE, SUBDL_KEY_FILE,
    PLAYLIST_FILE, POSTERS_CACHE_DIR, get_plugin_dir
)
from ..core.paths import get_plugin_dir
BACKGROUND_SETTINGS = os.path.join(get_plugin_dir(), "icons", "settings.png")

class SettingsScreen(Screen):
    skin = """
        <screen name="CiefpSfilesSettings" position="center,center" size="1400,950"
                title="..:: CiefpSfiles Settings ::.." backgroundColor="#011a2e">
            <widget name="menu" position="50,50" size="700,800" scrollbarMode="showOnDemand"
                    itemHeight="45" font="Regular;26" backgroundColor="#011a2e"/>
            <widget name="status" position="50,800" size="1300,40" font="Regular;26"
                    foregroundColor="#00FF00" backgroundColor="#011a2e"/>
            <widget name="background" position="800,0" size="500,800" pixmap="%s" alphatest="on"/>
            <ePixmap pixmap="buttons/red.png" position="50,880" size="35,35" alphatest="blend"/>
            <eLabel text="Cancel" position="100,870" size="200,50" font="Regular;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
            <ePixmap pixmap="buttons/green.png" position="320,880" size="35,35" alphatest="blend"/>
            <eLabel text="Save" position="370,870" size="200,50" font="Regular;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """ % BACKGROUND_SETTINGS

    # Nove proširene liste jezika
    TMDB_LANGUAGES = [
        "en", "sr", "hr", "bs", "sl", "mk", "cs", "sk", "hu", "ro",
        "bg", "el", "de", "fr", "es", "it", "pt", "nl", "sv", "no",
        "da", "fi", "ru", "uk", "pl", "tr", "ar", "he", "ja", "ko",
        "zh", "th", "vi"
    ]

    TRANSLATE_LANGUAGES = [
        "sr", "hr", "bs", "sl", "mk", "en", "de", "fr", "es", "it",
        "ru", "pt", "pl", "cs", "hu", "ro", "bg", "el", "tr", "nl",
        "sv", "da", "fi", "no", "he", "ja", "ko", "zh", "hi", "vi"
    ]

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["menu"] = MenuList([])
        self["status"] = Label("Settings")
        self["background"] = Pixmap()
        
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.save_settings,
                "ok": self.on_ok,
                "left": self.on_left,
                "right": self.on_right,
            }, -1)
            
        self.onLayoutFinish.append(self.build_menu)

    def _get_plugin_dir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read_key(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def _write_key(self, path, value):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(value.strip())
            return True
        except Exception as e:
            print(f"[CiefpSfiles] Error saving key: {e}")
            return False

    def _get_cache_size(self):
        total_size = 0
        if os.path.exists(POSTERS_CACHE_DIR):
            for dirpath, _, filenames in os.walk(POSTERS_CACHE_DIR):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # U MB

    def _clear_cache(self):
        if os.path.exists(POSTERS_CACHE_DIR):
            try:
                shutil.rmtree(POSTERS_CACHE_DIR)
                os.makedirs(POSTERS_CACHE_DIR)
                self["status"].setText("Cache cleared successfully!")
            except Exception as e:
                self["status"].setText(f"Error clearing cache: {e}")
        else:
            self["status"].setText("Cache is already empty.")

    def build_menu(self):
        # Provera ključeva
        tmdb = "[SET]" if self._read_key(TMDB_KEY_FILE) else "[EMPTY]"
        omdb = "[SET]" if self._read_key(OMDB_KEY_FILE) else "[EMPTY]"
        groq = "[SET]" if self._read_key(GROQ_KEY_FILE) else "[EMPTY]"
        subdl = "[SET]" if self._read_key(SUBDL_KEY_FILE) else "[EMPTY]"

        # Uzimamo vrednosti iz config-a
        t_lang = config.plugins.ciefpsfiles.tmdb_language.value
        g_trans = "YES" if config.plugins.ciefpsfiles.groq_plot_translation.value else "NO"
        p_live = config.plugins.ciefpsfiles.player_type_live.value
        p_vod = config.plugins.ciefpsfiles.player_type_vod.value
        skin_type = config.plugins.ciefpsfiles.skin_type.value

        # ISPRAVLJENO: Uzimamo translate_language za GROQ, a subtitle_language za titlove
        translate_lang = getattr(config.plugins.ciefpsfiles, 'translate_language',
                                 type('obj', (object,), {'value': 'sr'})).value
        sub_lang = getattr(config.plugins.ciefpsfiles, 'subtitle_language',
                           type('obj', (object,), {'value': 'sr'})).value

        epg_auto = "YES" if getattr(config.plugins.ciefpsfiles, 'epg_auto_update',
                                    type('obj', (object,), {'value': True})).value else "NO"
        adult = "YES" if getattr(config.plugins.ciefpsfiles, 'adult_content',
                                 type('obj', (object,), {'value': False})).value else "NO"

        cache_mb = self._get_cache_size()

        items = [
            f"TMDB API Key:         {tmdb}",  # 0
            f"OMDB API Key:         {omdb}",  # 1
            f"GROQ API Key:         {groq}",  # 2
            f"SUBDL API Key:        {subdl}",  # 3
            "----------------------------------------",  # 4
            f"Skin Type:            {skin_type}",  # 5
            f"TMDB Language:        {t_lang}",  # 6
            f"GROQ Translate Plot:  {g_trans}",  # 7
            f"GROQ Translate Lang:  {translate_lang}",  # 8 <-- ISPRAVLJENO (bilo sub_lang)
            f"Live Player Type:     {p_live}",  # 9
            f"VOD Player Type:      {p_vod}",  # 10
            f"Subtitle Language:    {sub_lang}",  # 11
            f"EPG Auto Update:      {epg_auto}",  # 12
            f"Adult Content:        {adult}",  # 13
            "----------------------------------------",  # 14
            f"Clear Cache:          {cache_mb:.1f} MB",  # 15
            ">>> TEST TMDB CONNECTION <<<"  # 16
        ]

        self["menu"].setList(items)

    def on_ok(self):
        idx = self["menu"].getSelectedIndex()
        if idx == 0:
            self.edit_key("TMDB API Key", TMDB_KEY_FILE)
        elif idx == 1:
            self.edit_key("OMDB API Key", OMDB_KEY_FILE)
        elif idx == 2:
            self.edit_key("GROQ API Key", GROQ_KEY_FILE, config_field="groq_api_key")
        elif idx == 3:
            self.edit_key("SUBDL API Key", SUBDL_KEY_FILE)
        elif idx == 15:
            self._clear_cache()
        elif idx == 16:
            self.test_tmdb()

    def _change_option(self, idx, direction):
        if idx == 5:  # Skin Type
            choices = ["classic", "modern"]
            current = config.plugins.ciefpsfiles.skin_type.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.skin_type.value = choices[new_idx]

        elif idx == 6:  # TMDB Language
            choices = self.TMDB_LANGUAGES
            current = config.plugins.ciefpsfiles.tmdb_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.tmdb_language.value = choices[new_idx]

        elif idx == 7:  # GROQ Translate Plot
            config.plugins.ciefpsfiles.groq_plot_translation.value = not config.plugins.ciefpsfiles.groq_plot_translation.value

        elif idx == 8:  # GROQ Translate Lang
            choices = self.TRANSLATE_LANGUAGES
            current = config.plugins.ciefpsfiles.translate_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.translate_language.value = choices[new_idx]

        elif idx == 9:  # Live Player
            choices = ["5002", "5001", "4097"]
            current = config.plugins.ciefpsfiles.player_type_live.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.player_type_live.value = choices[new_idx]

        elif idx == 10:  # VOD Player
            choices = ["5002", "5001", "4097"]
            current = config.plugins.ciefpsfiles.player_type_vod.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.player_type_vod.value = choices[new_idx]

        elif idx == 11:  # Subtitle Language
            choices = self.TRANSLATE_LANGUAGES
            current = config.plugins.ciefpsfiles.subtitle_language.value
            new_idx = (choices.index(current) + direction) % len(choices) if current in choices else 0
            config.plugins.ciefpsfiles.subtitle_language.value = choices[new_idx]

        elif idx == 12:  # EPG Auto Update
            config.plugins.ciefpsfiles.epg_auto_update.value = not config.plugins.ciefpsfiles.epg_auto_update.value

        elif idx == 13:  # Adult Content
            config.plugins.ciefpsfiles.adult_content.value = not config.plugins.ciefpsfiles.adult_content.value

        self.build_menu()

    def on_left(self):
        idx = self["menu"].getSelectedIndex()
        self._change_option(idx, -1)

    def on_right(self):
        idx = self["menu"].getSelectedIndex()
        self._change_option(idx, 1)

    def edit_key(self, title, filename_or_config, is_file=True, config_field=None):
        if is_file:
            current = self._read_key(filename_or_config)
        else:
            current = filename_or_config.value

        def cb(res):
            if res is not None:
                if is_file:
                    if self._write_key(filename_or_config, res):
                        # Sinhronizuj u config ako je zadato polje
                        if config_field:
                            try:
                                getattr(config.plugins.ciefpsfiles, config_field).value = res.strip()
                            except Exception as e:
                                print(f"[CiefpSfiles] Config sync error: {e}")
                        self["status"].setText(f"{title} saved.")
                else:
                    filename_or_config.value = res
                    self["status"].setText(f"{title} saved.")
                self.build_menu()

        self.session.openWithCallback(cb, VirtualKeyBoard, title=title, text=current)

    def save_settings(self):
        config.plugins.ciefpsfiles.save()
        self["status"].setText("Settings saved!")
        self.close()

    def test_tmdb(self):
        api_key = self._read_key(TMDB_KEY_FILE)
        if not api_key:
            self["status"].setText("TMDB Key is empty! Please set it first.")
            return

        self["status"].setText("Testing TMDB connection...")

        def worker():
            try:
                url = f"https://api.themoviedb.org/3/movie/550?api_key={api_key}&language=en-US"
                response = requests.get(url, timeout=10, verify=False)
                if response.status_code == 200:
                    msg = f"Success! TMDB returned: {response.json().get('title', 'Unknown')}"
                else:
                    msg = f"HTTP Error: {response.status_code}"
            except Exception as e:
                msg = f"Connection Error: {str(e)}"

            from enigma import eTimer
            self._test_timer = eTimer()
            self._test_timer.callback.append(lambda: self["status"].setText(msg))
            self._test_timer.start(10, True)

        threading.Thread(target=worker, daemon=True).start()
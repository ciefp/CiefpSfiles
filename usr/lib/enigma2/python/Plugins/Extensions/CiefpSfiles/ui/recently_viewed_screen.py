# -*- coding: utf-8 -*-
import os
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER

from ..core.recently_viewed import get_viewed_items
from ..core.config import config

def _load_pixmap_safe(path):
    if path and os.path.exists(path):
        try:
            return loadPNG(path)
        except Exception:
            return None
    return None

def _get_icon_path(icon_name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", icon_name)

class RecentlyViewedScreen(Screen):
    skin = """
        <screen name="CiefpXfilesRecentlyViewed" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>
                    
            <!-- DESNI PANEL: Poster -->
            <widget name="poster" position="1320,110" size="500,750"
                    alphatest="blend" zPosition="2"/>
        
            <widget name="left_list" position="40,110" size="900,850"
                    scrollbarMode="showOnDemand" itemHeight="60"
                    font="Regular;28" backgroundColor="#011a2e"/>
            <widget name="status" position="40,980" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
            <ePixmap pixmap="buttons/red.png" position="0,1020" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1015" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
            <ePixmap pixmap="buttons/green.png" position="240,1020" size="35,35" alphatest="blend"/>
            <eLabel text="OPEN" position="290,1015" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#008000" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal

        self["title"] = Label("..:: Recently Viewed ::..")
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(60)
        self["left_list"].l.setFont(0, gFont("Regular", 28))
        self["status"] = Label("")
        self["poster"] = Pixmap()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "green": self.open_selected,
                "ok": self.open_selected,
                "up": self.on_up,
                "down": self.on_down,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        self._render_menu()
        self._set_poster(None)  # Automatski povlači placeholder.png

    def _set_poster(self, image_path):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if image_path and os.path.exists(image_path):
            path = image_path
        else:
            path = os.path.join(plugin_dir, "icons", "placeholder.png")

        px = _load_pixmap_safe(path)
        if px and self["poster"].instance:
            self["poster"].instance.setPixmap(px)

    def _render_menu(self):
        items = []
        icon_folder = _get_icon_path("icon_folder.png")
        recent_vod = get_viewed_items(self.portal.get("host", ""), "vod")
        recent_series = get_viewed_items(self.portal.get("host", ""), "series")

        movies_label = "Movies (%d)" % len(recent_vod)
        series_label = "Series (%d)" % len(recent_series)

        if os.path.exists(icon_folder):
            items.append([
                ("VOD", movies_label),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(40, 40), png=loadPNG(icon_folder)),
                MultiContentEntryText(pos=(60, 0), size=(800, 60), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text=movies_label)
            ])
            items.append([
                ("SERIES", series_label),
                MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(40, 40), png=loadPNG(icon_folder)),
                MultiContentEntryText(pos=(60, 0), size=(800, 60), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text=series_label)
            ])
        else:
            items.append([
                ("VOD", movies_label),
                MultiContentEntryText(pos=(0, 0), size=(850, 60), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text=movies_label)
            ])
            items.append([
                ("SERIES", series_label),
                MultiContentEntryText(pos=(0, 0), size=(850, 60), font=0,
                                      flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                      text=series_label)
            ])

        self._list_to_type = {
            0: "VOD",
            1: "SERIES",
        }

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText("Select Movies or Series to view recently played items.")

    def open_selected(self):
        idx = self["left_list"].getSelectedIndex()
        item_type = getattr(self, "_list_to_type", {}).get(idx)
        if not item_type:
            return

        # OVDE JE BILA GREŠKA: ciefpxfiles -> ciefpsfiles
        skin_type = config.plugins.ciefpsfiles.skin_type.value

        if skin_type == "modern":
            if item_type == "VOD":
                from .modern_vod_screen import ModernVODScreen
                self.session.open(ModernVODScreen, self.portal, "RECENT_VOD", "★ Recently Viewed")
            else:
                from .modern_series_screen import ModernSeriesScreen
                self.session.open(ModernSeriesScreen, self.portal, "RECENT_SERIES", "★ Recently Viewed")
        else:
            from .main_screen import MainScreen
            self.session.open(
                MainScreen,
                self.portal,
                None,
                start_view="VOD" if item_type == "VOD" else "SERIES",
                start_category="RECENT_VOD" if item_type == "VOD" else "RECENT_SERIES"
            )

    def on_up(self):
        try:
            self["left_list"].up()
        except Exception:
            pass

    def on_down(self):
        try:
            self["left_list"].down()
        except Exception:
            pass
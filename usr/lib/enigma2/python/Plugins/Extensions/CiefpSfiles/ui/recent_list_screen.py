# -*- coding: utf-8 -*-
import os
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eServiceReference

from ..core.recently_viewed import get_viewed_items
from ..core.config import config
from ..core.stalker_api import StalkerAPI  # <-- STALKER API

def _get_icon_path(icon_name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", icon_name)

class RecentListScreen(Screen):
    skin = """
        <screen name="CiefpSfilesRecentList" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>
            <widget name="left_list" position="40,110" size="900,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>
            <widget name="status" position="40,980" size="1000,40"
                    font="Regular;24" halign="left" valign="center"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
            <ePixmap pixmap="buttons/red.png" position="0,1020" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1015" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, portal, item_type):
        Screen.__init__(self, session)
        self.session = session
        self.portal = portal
        self.item_type = item_type
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])

        title_text = "Recently Viewed Movies" if item_type == "VOD" else "Recently Viewed Series"
        self["title"] = Label(f"..:: {title_text} ::..")
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        self["status"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "ok": self.open_selected,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        self._render_list()

    def _render_list(self):
        items = []
        key = "vod" if self.item_type == "VOD" else "series"
        recent = get_viewed_items(self.portal.get("host", ""), key)

        icon_name = "icon_film.png" if self.item_type == "VOD" else "icon_tv.png"
        icon = _get_icon_path(icon_name)
        icon_exists = os.path.exists(icon)

        for item in recent:
            name = item.get("name", "Unknown")
            if icon_exists:
                items.append([
                    (name, item.get("id")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
            else:
                items.append([
                    (name, item.get("id")),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])

        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText("Loaded {} items.".format(len(recent)))

    def open_selected(self):
        item = self["left_list"].getCurrent()
        if not item:
            return
        name = item[0]
        item_id = item[1]

        if self.item_type == "VOD":
            ext = "mp4"
            url = self.api.build_movie_url(item_id, ext)
            self._play(name, url)
        else:
            msg = "Series recently viewed: {}\n\nOpening series is available in Modern skin.".format(name)
            self.session.open(
                MessageBox,
                msg,
                MessageBox.TYPE_INFO, timeout=3
            )

    def _play(self, title, url):
        try:
            player_type = config.plugins.ciefpsfiles.player_type_vod.value  # <-- CIEPSFILES
        except Exception:
            player_type = "4097"

        encoded = url.replace(":", "%3a")
        safe_title = title.replace(":", " -").replace("\n", " ")
        ref_str = "%s:0:1:0:0:0:0:0:0:0:%s:%s" % (player_type, encoded, safe_title)
        try:
            ref = eServiceReference(ref_str)
            if not ref.valid():
                self["status"].setText("Invalid reference")
                return
        except Exception as e:
            self["status"].setText("Error: %s" % e)
            return
        try:
            self.session.open(MoviePlayer, ref)
        except Exception as e:
            self["status"].setText("Play error: %s" % e)
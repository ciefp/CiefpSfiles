# -*- coding: utf-8 -*-
#
# vod_groups_screen.py - Ekran sa listom VOD grupa (kategorija)
#
from __future__ import absolute_import, print_function

import os
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER

from ..core.stalker_api import StalkerAPI
from .modern_vod_screen import ModernVODScreen, _load_pixmap_safe

def _get_icon_path(icon_name):
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(plugin_dir, "icons", icon_name)

class VODGroupsScreen(Screen):
    skin = """
        <screen name="CiefpSfilesVODGroups" position="0,0" size="1920,1080"
                backgroundColor="#011a2e">

            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF"
                    backgroundColor="#011a2e" transparent="1"/>

            <widget name="left_list" position="40,110" size="900,850"
                    scrollbarMode="showOnDemand" itemHeight="50"
                    font="Regular;26" backgroundColor="#011a2e"/>
            <widget name="logo" position="1300,100" size="560,780" alphatest="blend" zPosition="2"/>
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
        
        self.api = StalkerAPI(portal["host"], portal["mac"], portal["password"])
        
        self.categories = []
        
        self["title"] = Label(f"..:: {portal.get('name', '')} - Movies ::..")
        self["left_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["left_list"].l.setItemHeight(50)
        self["left_list"].l.setFont(0, gFont("Regular", 26))
        self["logo"] = Pixmap()
        self["status"] = Label("")

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
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(plugin_dir, "icons", "plugin_logo.png")
        if os.path.exists(logo_path):
            px = _load_pixmap_safe(logo_path)
            if px and self["logo"].instance:
                self["logo"].instance.setPixmap(px)

        self["status"].setText("Loading VOD categories...")
        ok, data, err = self.api.get_vod_categories()
        if ok:
            self.categories = data
            self._render_categories()
        else:
            self["status"].setText(f"Error: {err}")

    def _render_categories(self):
        items = []
        icon_folder = _get_icon_path("icon_folder.png")
        
        for idx, cat in enumerate(self.categories):
            name = cat.get('category_name', 'Unknown')
            if os.path.exists(icon_folder):
                items.append([
                    (name, cat.get("category_id"), cat.get("category_name")),
                    MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(30, 30), png=loadPNG(icon_folder)),
                    MultiContentEntryText(pos=(50, 0), size=(800, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
            else:
                items.append([
                    (name, cat.get("category_id"), cat.get("category_name")),
                    MultiContentEntryText(pos=(0, 0), size=(850, 50), font=0,
                                          flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                          text=name)
                ])
                
        self["left_list"].setList(items)
        self["left_list"].moveToIndex(0)
        self["status"].setText(f"Loaded {len(self.categories)} categories.")

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

    def open_selected(self):
        idx = self["left_list"].getSelectedIndex()
        if 0 <= idx < len(self.categories):
            cat = self.categories[idx]
            self.session.open(
                ModernVODScreen,
                self.portal,
                cat.get("category_id"),
                cat.get("category_name")
            )
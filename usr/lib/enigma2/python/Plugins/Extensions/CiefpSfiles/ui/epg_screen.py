# -*- coding: utf-8 -*-
import os
import threading
import time
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Screens.Screen import Screen
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER

class EPGScreen(Screen):
    skin = """
        <screen name="CiefpEPGScreen" position="0,0" size="1920,1080" backgroundColor="#011a2e">
            <widget name="title" position="0,20" size="1920,60" font="Bold;42"
                    halign="center" valign="center" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="channel_name" position="50,100" size="1000,40" font="Bold;32"
                    foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1"/>
            
            <widget name="epg_list" position="50,160" size="1820,750" 
                    scrollbarMode="showOnDemand" itemHeight="90"
                    font="Regular;26" backgroundColor="#011a2e"/>

            <!-- DUGMAD -->
            <ePixmap pixmap="buttons/red.png" position="0,1005" size="35,35" alphatest="blend"/>
            <eLabel text="EXIT" position="50,1000" size="180,45" font="Bold;28"
                    foregroundColor="white" backgroundColor="#800000" halign="center" valign="center"/>
        </screen>
    """

    def __init__(self, session, api, stream_id, channel_name):
        Screen.__init__(self, session)
        self.session = session
        self.api = api
        self.stream_id = stream_id
        self.channel_name = channel_name

        self["title"] = Label("..:: EPG Guide ::..")
        self["channel_name"] = Label(f"Channel: {channel_name}")
        
        self["epg_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["epg_list"].l.setItemHeight(90)
        self["epg_list"].l.setFont(0, gFont("Regular", 26))

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "cancel": self.close,
                "red": self.close,
            }, -1
        )

        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        threading.Thread(target=self._fetch_full_epg, daemon=True).start()

    def _fetch_full_epg(self):
        import base64
        import time

        try:
            ok, data, error = self.api.get_short_epg(self.stream_id, limit=100)
            if not ok:
                raise RuntimeError(error or "EPG request failed")

            listings = data.get("epg_listings", [])
            
            items = []
            now = int(time.time())
            last_date = None
            
            for listing in listings:
                try:
                    start_ts = int(listing.get("start_timestamp") or listing.get("start") or 0)
                    stop_ts = int(listing.get("stop_timestamp") or listing.get("end") or 0)
                    
                    if stop_ts < now:
                        continue

                    # Format datuma i vremena
                    current_date = time.strftime("%d.%m.%Y", time.localtime(start_ts)) if start_ts else "--.--.----"
                    start_time = time.strftime("%H:%M", time.localtime(start_ts)) if start_ts else "--:--"
                    end_time = time.strftime("%H:%M", time.localtime(stop_ts)) if stop_ts else "--:--"
                    
                    # Dodaj separator za novi dan
                    if current_date != last_date:
                        last_date = current_date
                        # Dodaj datumski separator
                        items.append([
                            ("", ""),
                            MultiContentEntryText(pos=(0, 0), size=(1800, 40), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text=f"---------------------------------------- {current_date} ----------------------------------------"),
                            MultiContentEntryText(pos=(0, 40), size=(1800, 50), font=0,
                                                  flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                                  text="")
                        ])
                    
                    try:
                        encoded_title = listing.get("title", "")
                        title = base64.b64decode(encoded_title).decode("utf-8", errors="ignore") if encoded_title else ""
                    except Exception:
                        title = listing.get("title", "No Title")
                        
                    try:
                        encoded_desc = listing.get("description", "")
                        desc = base64.b64decode(encoded_desc).decode("utf-8", errors="ignore") if encoded_desc else ""
                    except Exception:
                        desc = listing.get("description", "")

                    # Skrati opis ako je predugačak
                    desc_short = desc[:150] + "..." if len(desc) > 150 else desc

                    # Format: Vreme | Naslov
                    display_text = f"{start_time} - {end_time}  |  {title}"

                    items.append([
                        (display_text, desc),
                        MultiContentEntryText(pos=(0, 0), size=(1800, 35), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=display_text),
                        MultiContentEntryText(pos=(0, 40), size=(1800, 40), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text=desc_short),
                        # Separator linija
                        MultiContentEntryText(pos=(0, 85), size=(1800, 5), font=0,
                                              flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                              text="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
                    ])
                except Exception as e:
                    print(f"[EPGScreen] Error parsing listing: {e}")

            from enigma import eTimer
            def _update_ui():
                if not items:
                    self["epg_list"].setList([("", "No EPG data available for this channel.")])
                else:
                    self["epg_list"].setList(items)
                    
            self._timer = eTimer()
            self._timer.callback.append(_update_ui)
            self._timer.start(10, True)

        except Exception as e:
            print(f"[EPGScreen] Fetch error: {e}")

# -*- coding: utf-8 -*-
#
# player.py - Puštanje strimova (podrška za exteplayer3)
#
from __future__ import absolute_import, print_function

from enigma import eServiceReference

# Mapiranje tipova plejera
PLAYER_TYPES = {
    "4097": "GStreamer (4097)",
    "5001": "GStreamer (5001)",
    "5002": "Exteplayer3 (5002)",
}


def play_stream(session, url, player_type="5002", title="Unknown"):
    """
    Pušta strim koristeći zadati tip plejera.
    Dodaje 'title' kako bi Enigma2 prikazao lepo ime umesto imena fajla.
    """
    if not url:
        return False, "URL is empty"

    try:
        # Enigma2 zahteva da se URL kodira
        encoded_url = url.replace(":", "%3a")

        # Čistimo naslov od nevalidnih karaktera za referencu (dvotačka je zabranjena)
        safe_title = title.replace(":", " -").replace("\n", " ")

        # Formiramo referencu: TIP:0:1:0:0:0:0:0:0:0:URL:NASLOV
        ref_str = f"{player_type}:0:1:0:0:0:0:0:0:0:{encoded_url}:{safe_title}"
        ref = eServiceReference(ref_str)

        if not ref.valid():
            return False, "Invalid service reference"

        session.nav.playService(ref)
        return True, None
    except Exception as e:
        print(f"[CiefpSfiles] Play error: {e}")
        return False, str(e)
    False, str(e)
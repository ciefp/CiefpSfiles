# CiefpSFiles

**CiefpSFiles** is an Enigma2 Stalker/Ministra portal player derived from
the existing CiefpXfiles user interface. The original screen layouts, metadata
features, player choices, posters, subtitles, and live/VOD/series navigation
are retained while the Xtream transport has been replaced by a MAC-authenticated
Stalker backend.

## Portal file

The default file is `/etc/enigma2/CiefpSFiles/playlist.txt`.

```text
Host:http://portal.example:8080
Mac:00:1A:79:12:34:56
Alias:Living room
Device_Password:optional
```

The compact EStalker-style layout is also accepted:

```text
http://portal.example:8080
00:1A:79:12:34:56 # Living room
00:1A:79:AA:BB:CC # Bedroom
```

## Backend

The independent implementation in `core/stalker_api.py` supports:

- MAG-style handshake and bearer-token authentication
- modern `portal.php` and legacy `server/load.php` discovery
- live genres and channels
- live short EPG
- VOD and series categories/listings
- automatic multi-page VOD and series retrieval
- token-expiry re-handshake and request retry
- MAG identity and optional second-stage password parameters
- on-demand `create_link` resolution
- direct `ffmpeg`/`auto` command playback and custom-link resolution
- Stalker season rows expanded into Ciefp episode records
- optional device password storage

Full EPG/catch-up, favourites, hidden categories, watched/resume state, and
additional search/sorting features are intentionally outside this conversion.

The Stalker protocol behaviour was informed by the public
[kiddac/EStalker](https://github.com/kiddac/EStalker) project, with permission
from its author as stated by the requester. No source file was copied verbatim;
the backend here is a new compatibility implementation designed for the
CiefpXfiles UI data model.

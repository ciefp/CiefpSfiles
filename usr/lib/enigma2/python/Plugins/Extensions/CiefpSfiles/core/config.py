# -*- coding: utf-8 -*-
from Components.config import config, ConfigSubsection, ConfigText, ConfigSelection, ConfigYesNo, ConfigDirectory

# Inicijalizacija sekcije za naš plugin
config.plugins.ciefpsfiles = ConfigSubsection()

# API Ključevi
config.plugins.ciefpsfiles.tmdb_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpsfiles.omdb_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpsfiles.groq_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ciefpsfiles.subdl_api_key = ConfigText(default="", fixed_size=False)

# --- DEFINICIJA LISTE JEZIKA (zajednička za više opcija) ---
LANG_CHOICES = [
    ("sr", "Srpski"), ("hr", "Hrvatski"), ("bs", "Bosanski"),
    ("sl", "Slovenščina"), ("mk", "Македонски"), ("en", "English"),
    ("de", "Deutsch"), ("fr", "Français"), ("es", "Español"),
    ("it", "Italiano"), ("ru", "Русский"), ("pt", "Português"),
    ("pl", "Polski"), ("cs", "Čeština"), ("hu", "Magyar"),
    ("ro", "Română"), ("bg", "Български"), ("el", "Ελληνικά"),
    ("tr", "Türkçe"),
    ("nl", "Nederlands"),
    ("sv", "Svenska"),
    ("da", "Dansk"),
    ("fi", "Suomi"),
    ("no", "Norsk"),
    ("he", "עברית"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("zh", "中文"),
    ("hi", "हिन्दी"),
    ("vi", "Tiếng Việt"),
]

# DODATO: translate_language
config.plugins.ciefpsfiles.translate_language = ConfigSelection(default="sr", choices=LANG_CHOICES)
config.plugins.ciefpsfiles.tmdb_language = ConfigSelection(default="en", choices=LANG_CHOICES)
config.plugins.ciefpsfiles.subtitle_language = ConfigSelection(default="sr", choices=LANG_CHOICES)

# Putanje
config.plugins.ciefpsfiles.subtitle_location = ConfigText(default="/media/hdd/subtitles/", fixed_size=False)
config.plugins.ciefpsfiles.playlist_location = ConfigText(default="/etc/enigma2/CiefpStalkerFiles/playlist.txt", fixed_size=False)

# GROQ
config.plugins.ciefpsfiles.groq_plot_translation = ConfigYesNo(default=True)
config.plugins.ciefpsfiles.groq_model = ConfigSelection(default="openai/gpt-oss-20b", choices=[
    ("openai/gpt-oss-20b", "GPT-OSS 20B (Preporučeno)"),
    ("openai/gpt-oss-120b", "GPT-OSS 120B (Snažniji)"),
    ("qwen/qwen3.8-27b", "Qwen 3.8 27B"),
])

# Plejeri
PLAYER_CHOICES = [
    ("5002", "Exteplayer3 (5002)"),
    ("5001", "GStreamer (5001)"),
    ("4097", "GStreamer (4097)")
]
config.plugins.ciefpsfiles.player_type_live = ConfigSelection(default="5002", choices=PLAYER_CHOICES)
config.plugins.ciefpsfiles.player_type_vod = ConfigSelection(default="5002", choices=PLAYER_CHOICES)

# EPG i Ostalo
config.plugins.ciefpsfiles.epg_auto_update = ConfigYesNo(default=True)
config.plugins.ciefpsfiles.epg_interval_hours = ConfigSelection(default="12", choices=[
    ("6", "6 sati"), ("12", "12 sati"), ("24", "24 sata"), ("48", "48 sati")
])
config.plugins.ciefpsfiles.adult_content = ConfigYesNo(default=False)
config.plugins.ciefpsfiles.use_subssupport = ConfigYesNo(default=True)

# Tip skina (Classic / Modern)
config.plugins.ciefpsfiles.skin_type = ConfigSelection(default="classic", choices=[
    ("classic", "Classic"),
    ("modern", "Modern"),
])
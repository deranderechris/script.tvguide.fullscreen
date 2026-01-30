import sys
import os
import stat
import re
import time
import datetime
import sqlite3
import subprocess

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from vpnapi import VPNAPI


# --------------------------------------------------
# Logging
# --------------------------------------------------

def log(msg):
    xbmc.log(repr(msg), xbmc.LOGERROR)


# --------------------------------------------------
# Addon / Args
# --------------------------------------------------

ADDON = xbmcaddon.Addon(id='script.tvguide.fullscreen.reborn')

try:
    channel = sys.argv[1]
    start = sys.argv[2]
except Exception:
    log("Missing script arguments")
    sys.exit(1)


# --------------------------------------------------
# Datetime helpers
# --------------------------------------------------

def adapt_datetime(ts):
    return time.mktime(ts.timetuple())

def convert_datetime(ts):
    try:
        return datetime.datetime.fromtimestamp(float(ts))
    except Exception:
        return None


sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter('timestamp', convert_datetime)


# --------------------------------------------------
# Platform helpers
# --------------------------------------------------

def windows():
    return os.name == 'nt'


def android_get_current_appid():
    try:
        with open("/proc/%d/cmdline" % os.getpid(), encoding="utf-8", errors="ignore") as fp:
            return fp.read().rstrip("\0")
    except Exception:
        return ""


# --------------------------------------------------
# ffmpeg handling
# --------------------------------------------------

def ffmpeg_location():
    ffmpeg_src = xbmcvfs.translatePath(
        ADDON.getSetting('autoplaywiths.ffmpeg')
    )

    if xbmc.getCondVisibility('system.platform.android'):
        appid = android_get_current_appid()
        if not appid:
            return None

        ffmpeg_dst = f"/data/data/{appid}/ffmpeg"

        if (
            ADDON.getSetting('autoplaywiths.ffmpeg') != ADDON.getSetting('ffmpeg.last')
            or (not xbmcvfs.exists(ffmpeg_dst) and ffmpeg_src != ffmpeg_dst)
        ):
            try:
                xbmcvfs.copy(ffmpeg_src, ffmpeg_dst)
                ADDON.setSetting('ffmpeg.last', ADDON.getSetting('autoplaywiths.ffmpeg'))
            except Exception as e:
                log(e)

        ffmpeg = ffmpeg_dst
    else:
        ffmpeg = ffmpeg_src

    log(ffmpeg)

    if ffmpeg and xbmcvfs.exists(ffmpeg):
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
        except Exception as e:
            log(e)
        return ffmpeg

    xbmcgui.Dialog().notification("TVGF", "ffmpeg exe not found!")
    return None


# --------------------------------------------------
# Persist current playback
# --------------------------------------------------

ADDON.setSetting('playing.channel', channel)
ADDON.setSetting('playing.start', start)


# --------------------------------------------------
# Database
# --------------------------------------------------

db_path = xbmcvfs.translatePath(
    'special://profile/addon_data/script.tvguide.fullscreen/source.db'
)

try:
    conn = sqlite3.connect(
        db_path,
        timeout=30,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    conn.row_factory = sqlite3.Row
except Exception as e:
    log(e)
    sys.exit(1)


# --------------------------------------------------
# Resolve ffmpeg
# --------------------------------------------------

ffmpeg = ffmpeg_location()
if not ffmpeg:
    sys.exit(0)


# --------------------------------------------------
# Resolve stream URL
# --------------------------------------------------

cursor = conn.cursor()
cursor.execute(
    'SELECT stream_url FROM custom_stream_url WHERE channel=?',
    [channel]
)

row = cursor.fetchone()
if not row or not row[0]:
    sys.exit(0)

url = row[0]


# --------------------------------------------------
# Program info
# --------------------------------------------------

start_date = datetime.datetime.fromtimestamp(float(start))

cursor.execute(
    'SELECT DISTINCT * FROM programs WHERE channel=? AND start_date=?',
    [channel, start_date]
)

program = cursor.fetchone()
if not program:
    sys.exit(0)

title = program["title"]
is_movie = program["is_movie"]

safe_title = re.sub(r"[^\w' ]+", "", title, flags=re.UNICODE)

subfolder = "Movies" if is_movie == "Movie" else "TVShows"
base_folder = xbmcvfs.translatePath(
    ADDON.getSetting('autoplaywiths.folder')
)

folder = os.path.join(base_folder, subfolder, safe_title)
xbmcvfs.mkdirs(folder)

season = program["season"]
episode = program["episode"]
if season and episode:
    title = f"{title} S{season}E{episode}"

end_date = program["end_date"]
duration = end_date - start_date

before = int(ADDON.getSetting('autoplaywiths.before'))
after = int(ADDON.getSetting('autoplaywiths.after'))

seconds = int(duration.total_seconds()) + (before + after) * 60
seconds = min(seconds, 3600 * 4)


# --------------------------------------------------
# Resolve playable URL if needed
# --------------------------------------------------

if not url.startswith('http'):
    player = xbmc.Player()
    player.play(url)

    resolved_url = ""
    for _ in range(30):
        time.sleep(1)
        if player.isPlaying():
            resolved_url = player.getPlayingFile()
            break

    player.stop()
    url = resolved_url

if not url:
    sys.exit(0)


# --------------------------------------------------
# Recording
# --------------------------------------------------

name = "%s - %s - %s" % (
    re.sub(r"[^\w' ]+", "", channel, flags=re.UNICODE),
    re.sub(r"[^\w' ]+", "", title, flags=re.UNICODE),
    time.strftime('%Y-%m-%d %H-%M')
)

filename = os.path.join(folder, name + ".ts")

cmd = [
    ffmpeg,
    "-y",
    "-i", url,
    "-reconnect", "1",
    "-reconnect_at_eof", "1",
    "-reconnect_streamed", "1",
    "-reconnect_delay_max", "300",
    "-t", str(seconds),
    "-c", "copy",
    "-f", "mpegts",
    "-"
]

log(("ffmpeg start", cmd))

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    shell=windows()
)

outfile = xbmcvfs.File(filename, 'wb')

while True:
    data = process.stdout.read(1024 * 1024)
    if not data:
        if process.poll() is not None:
            break
        time.sleep(0.1)
        continue
    outfile.write(data)

outfile.close()
process.wait()

log(("ffmpeg done", cmd))


# --------------------------------------------------
# PlayWith / VPN handling
# --------------------------------------------------

script = "special://profile/addon_data/script.tvguide.fullscreen/playwith.py"
if xbmcvfs.exists(script):
    xbmc.executebuiltin(f'RunScript({script},{channel},{start})')

core = ADDON.getSetting('autoplaywiths.player')
if not core:
    sys.exit(0)

if xbmc.getCondVisibility("System.HasAddon(service.vpn.manager)"):
    try:
        if ADDON.getSetting('vpnmgr.connect') == "true":
            vpndefault = ADDON.getSetting('vpnmgr.default') == "true"
            api = VPNAPI()
            if url.startswith('plugin://'):
                api.filterAndSwitch(url, 0, vpndefault, True)
            else:
                if vpndefault:
                    api.defaultVPN(True)
    except Exception:
        pass

xbmc.executebuiltin(f'PlayWith({core})')
xbmc.executebuiltin(f'PlayMedia({url})')

sys.exit(0)

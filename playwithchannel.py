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

    if ffmpeg and xbmcvfs.exists(ffmpeg):
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
        except Exception:
            pass
        return ffmpeg

    xbmcgui.Dialog().notification("TVGF", "ffmpeg executable not found")
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
# Resolve stream URL
# --------------------------------------------------

ffmpeg = ffmpeg_location()
if not ffmpeg:
    sys.exit(0)

cursor = conn.cursor()
cursor.execute(
    'SELECT stream_url FROM custom_stream_url WHERE channel=?',
    [channel]
)

row = cursor.fetchone()
if not row or not row[0]:
    sys.exit(0)

stream_url = row[0]


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
base_folder = ADDON.getSetting('autoplaywiths.folder')

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
# Resolve actual playing URL
# --------------------------------------------------

player = xbmc.Player()
player.play(stream_url)

resolved_url = ""
for _ in range(30):
    time.sleep(1)
    if player.isPlaying():
        resolved_url = player.getPlayingFile()
        break

player.stop()

if not resolved_url:
    sys.exit(0)


# --------------------------------------------------
# Recording
# --------------------------------------------------

filename = xbmcvfs.translatePath(
    os.path.join(
        folder,
        f"{re.sub(r'[^\w ]+', '', channel)} - "
        f"{re.sub(r'[^\w ]+', '', title)} - "
        f"{time.strftime('%Y-%m-%d %H-%M')}.ts"
    )
)

cmd = [
    ffmpeg,
    "-y",
    "-i", resolved_url,
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
sys.exit(0)
    else:
        xbmcgui.Dialog().notification("TVGF", "ffmpeg exe not found!")

sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter('timestamp', convert_datetime)

ADDON.setSetting('playing.channel',channel)
ADDON.setSetting('playing.start',start)

path = xbmc.translatePath('special://profile/addon_data/script.tvguide.fullscreen/source.db')
try:
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
except Exception as detail:
    xbmc.log("EXCEPTION: (script.tvguide.fullscreen)  %s" % detail, xbmc.LOGERROR)

ffmpeg = ffmpeg_location()
if ffmpeg:
    folder = ADDON.getSetting('autoplaywiths.folder')
    c = conn.cursor()
    c.execute('SELECT stream_url FROM custom_stream_url WHERE channel=?', [channel])
    row = c.fetchone()
    url = ""
    if row:
        url = row[0]
    if not url:
        quit()
    startDate = datetime.datetime.fromtimestamp(float(start))
    c.execute('SELECT DISTINCT * FROM programs WHERE channel=? AND start_date = ?', [channel,startDate])
    for row in c:
        title = row["title"]
        is_movie = row["is_movie"]
        foldertitle = re.sub(r"\?", '', title)
        foldertitle = re.sub(r":|<>/", '', foldertitle)
        subfolder = "TVShows"
        if is_movie == 'Movie':
            subfolder = "Movies"
        folder = "%s%s/%s/" % (folder, subfolder, foldertitle)
        if not xbmcvfs.exists(folder):
            xbmcvfs.mkdirs(folder)
        season = row["season"]
        episode = row["episode"]
        if season and episode:
            title += " S%sE%s" % (season, episode)
        endDate = row["end_date"]
        duration = endDate - startDate
        before = int(ADDON.getSetting('autoplaywiths.before'))
        after = int(ADDON.getSetting('autoplaywiths.after'))
        extra = (before + after) * 60
        #TODO start from now
        seconds = duration.seconds + extra
        if seconds > (3600*4):
            seconds = 3600*4
        break
    player = xbmc.Player()
    player.play(url)
    count = 30
    url = ""
    while count:
        count = count - 1
        time.sleep(1)
        if player.isPlaying():
            url = player.getPlayingFile()
            break
    time.sleep(1)
    player.stop()
    time.sleep(1)

    # Play with your own preferred player and paths
    if url:
        name = "%s - %s - %s" % (re.sub(r"[^\w' ]+", "", channel, flags=re.UNICODE),re.sub(r"[^\w' ]+", "", title, flags=re.UNICODE),time.strftime('%Y-%m-%d %H-%M'))
        #name = re.sub("\?",'',name)
        #name = re.sub(":|<>\/",'',name)
        #name = name.encode("cp1252")
        #name = re.sub(r"[^\w' ]+", "", name, flags=re.UNICODE)
        filename = xbmc.translatePath("%s%s.ts" % (folder,name))
        seconds = 3600*4
        #cmd = [ffmpeg, "-y", "-i", url, "-c", "copy", "-t", str(seconds), filename]
        #log(cmd)
        #p = Popen(cmd,shell=windows())

        cmd = [ffmpeg, "-y", "-i", url]
        cmd = cmd + ["-reconnect", "1", "-reconnect_at_eof", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "300",  "-t", str(seconds), "-c", "copy"]
        cmd = cmd + ['-f', 'mpegts','-']
        log(("start",cmd))

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=windows())
        video = xbmcvfs.File(filename,'wb')
        while True:
            data = p.stdout.read(1000000)
            if not data:
                break
            video.write(data)
        video.close()

        p.wait()
        log(("done",cmd))

    quit()

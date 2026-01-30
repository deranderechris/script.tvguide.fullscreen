# -*- coding: utf-8 -*-
#
# utils.py – Python 3 cleaned drop-in version
#
import json
import os
import re
from itertools import zip_longest
from typing import Any, Iterable

import requests
import xbmc
import xbmcgui
import xbmcvfs
from xbmcvfs import translatePath
import xml.etree.ElementTree as ET

from strings import ADDON

LOGO_TYPE_DEFAULT = 0
LOGO_TYPE_CUSTOM = 1
DEFAULT_LOGO_URL = 'https://s3.amazonaws.com/schedulesdirect/assets/stationLogos/'


# ============================================================================
# Exceptions
# ============================================================================

class SourceException(Exception):
    pass


class SourceUpdateCanceledException(SourceException):
    pass


class SourceNotConfiguredException(SourceException):
    pass


# ============================================================================
# Models
# ============================================================================

class Channel:
    def __init__(self, id, title, lineup, logo=None, streamUrl=None, visible=True, weight=-1):
        self.id = id
        self.title = title
        self.lineup = lineup
        self.logo = logo
        self.streamUrl = streamUrl
        self.visible = visible
        self.weight = weight

    def isPlayable(self):
        return bool(self.streamUrl)

    def __eq__(self, other):
        if not isinstance(other, Channel):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return (
            f"Channel(id={self.id}, title={self.title}, lineup={self.lineup}, "
            f"logo={self.logo}, streamUrl={self.streamUrl}, "
            f"visible={self.visible}, weight={self.weight})"
        )


class Program:
    def __init__(
        self,
        channel,
        title,
        sub_title,
        startDate,
        endDate,
        description,
        categories,
        imageLarge=None,
        imageSmall=None,
        notificationScheduled=None,
        autoplayScheduled=None,
        autoplaywithScheduled=None,
        season=None,
        episode=None,
        is_new=False,
        is_movie=False,
        language="en",
    ):
        self.channel = channel
        self.title = title
        self.sub_title = sub_title
        self.startDate = startDate
        self.endDate = endDate
        self.description = description
        self.categories = categories

        self.imageLarge = (
            re.sub(" ", "+", imageLarge)
            if imageLarge and imageLarge.startswith("http")
            else imageLarge
        )
        self.imageSmall = (
            re.sub(" ", "+", imageSmall)
            if imageSmall and imageSmall.startswith("http")
            else imageSmall
        )

        self.notificationScheduled = notificationScheduled
        self.autoplayScheduled = autoplayScheduled
        self.autoplaywithScheduled = autoplaywithScheduled
        self.season = season
        self.episode = episode
        self.is_new = is_new
        self.is_movie = is_movie
        self.language = language

    def __repr__(self):
        return (
            f"Program(channel={self.channel}, title={self.title}, "
            f"sub_title={self.sub_title}, startDate={self.startDate}, "
            f"endDate={self.endDate}, description={self.description}, "
            f"categories={self.categories}, imageLarge={self.imageLarge}, "
            f"imageSmall={self.imageSmall}, season={self.season}, "
            f"episode={self.episode}, is_new={self.is_new}, "
            f"is_movie={self.is_movie})"
        )


# ============================================================================
# Helpers
# ============================================================================

def _safe_json_load(value: Any, default: Any):
    try:
        return json.loads(value)
    except Exception:
        return default


def grouper(n: int, iterable: Iterable, fillvalue=None):
    iterable = list(iterable)
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


# ============================================================================
# Settings
# ============================================================================

def save_setting(key, value, is_list=False):
    xbmc.log(
        f"[{ADDON.getAddonInfo('id')}] Trying to save setting: "
        f"key '{key}' / value '{value}'",
        xbmc.LOGDEBUG,
    )

    file_path = translatePath(
        os.path.join(ADDON.getAddonInfo("profile"), "settings.xml")
    )

    if not xbmcvfs.exists(file_path):
        generate_settings_file(file_path)

    tree = ET.parse(file_path)
    root = tree.getroot()
    updated = False

    for item in root.findall("setting"):
        if item.attrib.get("id") == key:
            if is_list:
                cur_values = _safe_json_load(item.attrib.get("value"), [])
                if isinstance(value, list):
                    for val in value:
                        if val not in cur_values:
                            cur_values.append(val)
                else:
                    if value not in cur_values:
                        cur_values.append(value)
                item.attrib["value"] = json.dumps(cur_values)
                ADDON.setSetting(key, json.dumps(cur_values))
            else:
                item.attrib["value"] = str(value)
                ADDON.setSetting(key, str(value))
            updated = True

    if updated:
        with open(file_path, "w", encoding="utf-8") as f:
            tree.write(f, encoding="unicode")

    return True


def generate_settings_file(target_path):
    source_path = translatePath(
        os.path.join(ADDON.getAddonInfo("path"), "resources", "settings.xml")
    )

    root_target = ET.Element("settings")
    tree_source = ET.parse(source_path)
    root_source = tree_source.getroot()

    for item in root_source.findall("category"):
        for setting in item.findall("setting"):
            if "id" in setting.attrib:
                value = setting.attrib.get("default", "")
                ET.SubElement(
                    root_target,
                    "setting",
                    id=setting.attrib["id"],
                    value=value,
                )

    tree_target = ET.ElementTree(root_target)

    with open(target_path, "w", encoding="utf-8") as f:
        tree_target.write(f, encoding="unicode")


def get_setting(key, is_list=False):
    value = ADDON.getSetting(key)
    if is_list:
        return _safe_json_load(value, [])
    return value


# ============================================================================
# Logos / Images
# ============================================================================

def get_logo(channel):
    logo = channel.logo
    logo_type = int(ADDON.getSetting("logos.source"))

    if logo and logo_type == LOGO_TYPE_DEFAULT:
        return logo

    logo_location = ADDON.getSetting("logos.folder")

    if not logo and logo_type == LOGO_TYPE_DEFAULT:
        logo = DEFAULT_LOGO_URL + "s" + str(channel.id) + "_h3_aa.png"
    elif logo_type == LOGO_TYPE_CUSTOM and logo and not logo.startswith(logo_location):
        logo = os.path.join(logo_location, f"{channel.title}.png")

    return logo


def reset_playing():
    path = translatePath(ADDON.getAddonInfo("profile"))
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

    proc_file = os.path.join(path, "proc")
    with open(proc_file, "w", encoding="utf-8") as f:
        f.write("")


def autocrop_image(image, border=0):
    from PIL import Image, ImageOps

    size = image.size
    bbox = image.getbbox()

    if bbox and size[0] == bbox[2] and size[1] == bbox[3]:
        inverted = ImageOps.invert(image.convert("RGB"))
        bbox = inverted.getbbox()

    if bbox:
        image = image.crop(bbox)

    width, height = image.size
    width += border * 2
    height += border * 2
    ratio = float(width) / height

    cropped_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cropped_image.paste(image, (border, border))

    logo_height = 450 // int(ADDON.getSetting("channels.per.page"))
    logo_height -= 2

    if not ADDON.getSettingBool("program.channel.logo"):
        cropped_image = cropped_image.resize(
            (int(logo_height * ratio), logo_height),
            Image.ANTIALIAS,
        )

    return cropped_image


def getLogo(title, ask=False, force=True):
    infile = translatePath(
        "special://profile/addon_data/script.tvguide.fullscreen/logos/temp.png"
    )
    outfile = translatePath(
        f"special://profile/addon_data/script.tvguide.fullscreen/logos/{title}.png"
    )

    if not force and xbmcvfs.exists(outfile):
        return outfile

    xbmcvfs.mkdirs(
        "special://profile/addon_data/script.tvguide.fullscreen/logos"
    )

    db_url = (
        "http://www.thelogodb.com/api/json/v1/4423/tvchannel.php?s="
        + re.sub(" ", "+", title)
    )

    try:
        data = requests.get(db_url, timeout=10).json()
    except Exception:
        return None

    if not data or "channels" not in data:
        return None

    channels = data["channels"]
    if not channels:
        return None

    if ask:
        names = [
            f"{c['strChannel']} [{c['strCountry']}]"
            for c in channels
        ]
        selected = xbmcgui.Dialog().select(
            f"Logo Source: {title}", names
        )
    else:
        selected = 0

    if selected < 0:
        return None

    logo = channels[selected].get("strLogoWide")
    if not logo:
        return None

    logo = re.sub("^https", "http", logo)

    try:
        img_data = requests.get(logo, timeout=10).content
    except Exception:
        return None

    with xbmcvfs.File(infile, "wb") as f:
        f.write(img_data)

    from PIL import Image

    image = Image.open(infile)
    image = autocrop_image(image, border=0)
    image.save(outfile)

    return outfile
    for item in root.findall('setting'):
        if item.attrib['id'] == key:
            if is_list:
                cur_values = item.attrib['value']
                if not cur_values:
                    cur_values = []
                else:
                    cur_values = json.loads(cur_values)
                if isinstance(value, list):
                    for val in value:
                        if val not in cur_values:
                            cur_values.append(val)
                else:
                    if value not in cur_values:
                        cur_values.append(value)
                item.attrib['value'] = json.dumps(cur_values)
                ADDON.setSetting(key, cur_values)
            else:
                item.attrib['value'] = value
                ADDON.setSetting(key, value)
            updated = True
    if updated:
        tree.write(file_path)
    return True


def generate_settings_file(target_path):
    source_path = xbmc.translatePath(
        os.path.join(ADDON.getAddonInfo('path'), 'resources', 'settings.xml'))
    root_target = ceT.Element("settings")
    tree_source = eT.parse(source_path)
    root_source = tree_source.getroot()
    for item in root_source.findall('category'):
        for setting in item.findall('setting'):
            if 'id' in setting.attrib:
                value = ''
                if 'default' in setting.attrib:
                    value = setting.attrib['default']
                ceT.SubElement(root_target, 'setting', id=setting.attrib['id'], value=value)
    tree_target = ceT.ElementTree(root_target)
    f = open(target_path, 'w')
    tree_target.write(f)
    f.close()


def get_setting(key, is_list=False):
    value = ADDON.getSetting(key)
    if value and is_list:
        value = json.loads(value)
    elif is_list:
        value = []
    return value


def grouper(n, iterable, fillvalue=None):
    """ grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx """
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)

#TODO this is wrong
def get_logo(channel):
    logo = channel.logo
    logo_type = int(ADDON.getSetting('logos.source'))
    if logo and logo_type == LOGO_TYPE_DEFAULT:
        return logo

    logo_location = ADDON.getSetting('logos.folder')
    if not logo and logo_type == LOGO_TYPE_DEFAULT:
        logo = DEFAULT_LOGO_URL + 's' + channel.id + '_h3_aa.png'
    elif logo_type == LOGO_TYPE_CUSTOM and not logo.startswith(logo_location):
        logo = logo_location + channel.title + '.png'
    return logo


def reset_playing():
    path = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    if not os.path.exists(path):
        os.mkdir(path)
    proc_file = os.path.join(path, 'proc')
    f = open(proc_file, 'w')
    f.write('')
    f.close()

def autocrop_image(image, border = 0):
    from PIL import Image, ImageOps
    size = image.size
    bb_image = image
    bbox = bb_image.getbbox()
    if (size[0] == bbox[2]) and (size[1] == bbox[3]):
        bb_image=bb_image.convert("RGB")
        bb_image = ImageOps.invert(bb_image)
        bbox = bb_image.getbbox()
    image = image.crop(bbox)
    (width, height) = image.size
    width += border * 2
    height += border * 2
    ratio = float(width)/height
    cropped_image = Image.new("RGBA", (width, height), (0,0,0,0))
    cropped_image.paste(image, (border, border))
    #TODO find epg height
    logo_height = 450 / int(ADDON.getSetting('channels.per.page'))
    logo_height = logo_height - 2
    if ADDON.getSetting('program.channel.logo') == "false":
        cropped_image = cropped_image.resize((int(logo_height*ratio), logo_height),Image.ANTIALIAS)
    return cropped_image

def getLogo(title,ask=False,force=True):
    infile = xbmc.translatePath("special://profile/addon_data/script.tvguide.fullscreen/logos/temp.png")
    outfile = xbmc.translatePath("special://profile/addon_data/script.tvguide.fullscreen/logos/%s.png" % title)
    if not force and xbmcvfs.exists(outfile):
        return outfile
    xbmcvfs.mkdirs("special://profile/addon_data/script.tvguide.fullscreen/logos")
    db_url = "http://www.thelogodb.com/api/json/v1/4423/tvchannel.php?s=%s" % re.sub(' ','+',title)
    try: json = requests.get(db_url).json()
    except: return None
    if json and "channels" in json:
        channels = json["channels"]
        if channels:
            if ask:
                names = ["%s [%s]" % (c["strChannel"],c["strCountry"]) for c in channels]
                d = xbmcgui.Dialog()
                selected = d.select("Logo Source: %s" % title,names)
            else:
                selected = 0
            if selected > -1:
                logo = channels[selected]["strLogoWide"]

                if not logo:
                    return None
                logo = re.sub('^https','http',logo)
                data = requests.get(logo).content
                f = xbmcvfs.File("special://profile/addon_data/script.tvguide.fullscreen/logos/temp.png","wb")
                f.write(data)
                f.close()
                from PIL import Image, ImageOps
                image = Image.open(infile)
                border = 0
                image = autocrop_image(image, border)
                image.save(outfile)
                logo = outfile
                return logo

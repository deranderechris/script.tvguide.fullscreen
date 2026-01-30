# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 derandere, Sarturn
# Python 3 update & fixes by derandere, Sarturn
#
# GPL v2+
#

import time
import datetime
import base64

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

import notification
import autoplay
import autoplaywith
import source


# ------------------------------------------------------------
# Addon
# ------------------------------------------------------------
ADDON = xbmcaddon.Addon(id='script.tvguide.fullscreen')


# ------------------------------------------------------------
# Logging helper
# ------------------------------------------------------------
def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('[script.tvguide.fullscreen] %s' % repr(msg), level)


# ------------------------------------------------------------
# Background Service
# ------------------------------------------------------------
class Service(object):

    def __init__(self):
        self.database = source.Database(True)
        self.database.initialize(self.onInit)

    def onInit(self, success):
        if success:
            log("Background update starting...", xbmc.LOGNOTICE)
            self.database.updateChannelAndProgramListCaches(self.onCachesUpdated)
        else:
            self.database.close()

    def onCachesUpdated(self):
        try:
            if ADDON.getSetting('notifications.enabled') == 'true':
                n = notification.Notification(
                    self.database,
                    ADDON.getAddonInfo('path')
                )
                n.scheduleNotifications()

            if ADDON.getSetting('autoplays.enabled') == 'true':
                n = autoplay.Autoplay(
                    self.database,
                    ADDON.getAddonInfo('path')
                )
                n.scheduleAutoplays()

            if ADDON.getSetting('autoplaywiths.enabled') == 'true':
                n = autoplaywith.Autoplaywith(
                    self.database,
                    ADDON.getAddonInfo('path')
                )
                n.scheduleAutoplaywiths()

        finally:
            self.database.close(None)
            log("Background update finished", xbmc.LOGNOTICE)

            if ADDON.getSetting('background.notify') == 'true':
                xbmcgui.Dialog().notification(
                    "TV Guide Fullscreen",
                    "Finished Updating",
                    sound=False
                )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == '__main__':

    # --------------------------------------------------------
    # Version handling (NO remote exec anymore!)
    # --------------------------------------------------------
    version = ADDON.getAddonInfo('version')
    if ADDON.getSetting('version') != version:
        ADDON.setSetting('version', version)
        log("Addon version updated to %s" % version, xbmc.LOGNOTICE)

    # --------------------------------------------------------
    # Cleanup stale DB locks
    # --------------------------------------------------------
    try:
        xbmcvfs.delete(
            'special://profile/addon_data/script.tvguide.fullscreen/source.db-journal'
        )
        xbmcvfs.delete(
            'special://profile/addon_data/script.tvguide.fullscreen/db.lock'
        )
    except Exception as e:
        log("Cleanup failed: %s" % e, xbmc.LOGWARNING)

    # --------------------------------------------------------
    # Autostart GUI
    # --------------------------------------------------------
    try:
        if ADDON.getSetting('autostart') == 'true':
            xbmc.executebuiltin(
                'RunAddon(script.tvguide.fullscreen)'
            )

        # ----------------------------------------------------
        # Background service loop
        # ----------------------------------------------------
        if ADDON.getSetting('background.service') == 'true':
            monitor = xbmc.Monitor()
            log("Background service started")

            if ADDON.getSetting('background.startup') == 'true':
                Service()
                ADDON.setSetting(
                    'last.background.update',
                    str(time.time())
                )

                if ADDON.getSetting('service.addon.folders') == 'true':
                    xbmc.executebuiltin(
                        'RunScript(special://home/addons/script.tvguide.fullscreen/ReloadAddonFolders.py)'
                    )

            while not monitor.abortRequested():

                # Interval-based
                if ADDON.getSetting('service.type') == '0':
                    interval = int(ADDON.getSetting('service.interval'))
                    waitTime = {
                        0: 7200,
                        1: 21600,
                        2: 43200,
                        3: 86400
                    }.get(interval, 21600)

                    last_ts = float(
                        ADDON.getSetting('last.background.update') or "0"
                    )
                    lastTime = datetime.datetime.fromtimestamp(last_ts)
                    nextTime = lastTime + datetime.timedelta(seconds=waitTime)
                    timeLeft = max(
                        int((nextTime - datetime.datetime.now()).total_seconds()),
                        0
                    )

                # Fixed-time daily
                else:
                    service_time = ADDON.getSetting('service.time')
                    now = datetime.datetime.now()

                    if service_time:
                        h, m = service_time.split(':')
                        nextTime = now.replace(
                            hour=int(h),
                            minute=int(m),
                            second=0,
                            microsecond=0
                        )
                        if nextTime <= now:
                            nextTime += datetime.timedelta(days=1)

                        timeLeft = max(
                            int((nextTime - now).total_seconds()),
                            0
                        )
                    else:
                        timeLeft = 3600

                log("Service waiting %d seconds" % timeLeft)

                if monitor.waitForAbort(timeLeft):
                    break

                log("Service triggered")
                Service()

                if ADDON.getSetting('service.addon.folders') == 'true':
                    xbmc.executebuiltin(
                        'RunScript(special://home/addons/script.tvguide.fullscreen/ReloadAddonFolders.py)'
                    )

                ADDON.setSetting(
                    'last.background.update',
                    str(time.time())
                )

    except source.SourceNotConfiguredException:
        log("Source not configured – service skipped", xbmc.LOGWARNING)

    except Exception as ex:
        log("Uncaught exception: %s" % ex, xbmc.LOGERROR)

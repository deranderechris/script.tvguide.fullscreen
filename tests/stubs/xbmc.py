LOGDEBUG = 0
LOGERROR = 1

def log(msg, level=LOGDEBUG):
    print('[xbmc.log]', msg)

def executebuiltin(cmd):
    print('[xbmc.exec]', cmd)

def translatePath(path):
    return path

def getInfoLabel(key):
    return ''

def sleep(ms):
    import time
    time.sleep(ms/1000.0)

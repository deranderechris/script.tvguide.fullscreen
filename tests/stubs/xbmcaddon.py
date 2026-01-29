class Addon:
    def __init__(self, id=None):
        self._id = id

    def getSetting(self, key):
        defaults = {
            'channels.per.page': '50',
            'date.long': 'true',
            'omdb': 'false',
        }
        return defaults.get(key, '')

    def getAddonInfo(self, key):
        return ''

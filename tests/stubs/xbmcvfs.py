import os

def exists(path):
    return os.path.exists(path)

class File:
    def __init__(self, path, mode='r'):
        self.path = path
        self.mode = mode
        self._f = None

    def write(self, data):
        d = data.encode('utf-8') if isinstance(data, str) else data
        with open(self.path, 'wb') as f:
            f.write(d)

    def read(self):
        try:
            with open(self.path, 'rb') as f:
                return f.read()
        except Exception:
            return b''

    def close(self):
        return

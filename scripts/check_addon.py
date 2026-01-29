#!/usr/bin/env python3
"""Check addon.xml for basic Kodi/Python compatibility.

Usage: python3 scripts/check_addon.py [path/to/addon.xml]
If no path given, uses ./addon.xml
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(path):
    p = Path(path)
    if not p.exists():
        print(f'ERROR: {p} not found')
        return 2
    tree = ET.parse(p)
    root = tree.getroot()
    addon_id = root.attrib.get('id')
    version = root.attrib.get('version')
    print(f'Addon: {addon_id}  version: {version}')

    requires = root.find('requires')
    if requires is None:
        print('WARNING: no <requires> section found')
    else:
        imports = requires.findall('import')
        found_xbmc_py = False
        min_xbmc_py = None
        for imp in imports:
            aid = imp.attrib.get('addon')
            ver = imp.attrib.get('version')
            print(f'  requires: {aid} {ver or ""}')
            if aid == 'xbmc.python':
                found_xbmc_py = True
                min_xbmc_py = ver

        if not found_xbmc_py:
            print('ERROR: addon does not declare xbmc.python import; Kodi may not know which Python to use')
            return 3

        # xbmc.python version strings are like 2.19.0 in Kodi addon.xml meaning xbmc.python 2.x => Kodi 19
        if min_xbmc_py:
            parts = min_xbmc_py.split('.')
            try:
                major = int(parts[0])
            except Exception:
                major = None
            if major is not None:
                if major >= 3:
                    print('NOTE: xbmc.python >=3 requested (Python 3). Good for Kodi 20+.')
                elif major == 2:
                    print('NOTE: xbmc.python 2.x requested (Python 2 compatibility). This addon was ported to Python 3; ensure target Kodi supports Python 3 (Kodi 19+ uses "xbmc.python" version 2.19.0 to indicate Python 3 API).')

    print('OK')
    return 0


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'addon.xml'
    sys.exit(main(path))

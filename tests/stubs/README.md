Test stubs for local Python3 smoke tests

Purpose:
- Provide minimal stand-ins for Kodi modules (`xbmc`, `xbmcgui`, `xbmcaddon`, `xbmcvfs`) so
  the repository can be imported and basic syntax/compatibility checks run under Python 3.

Usage:
- Run tests or imports with the stubs on `PYTHONPATH`:

```bash
PYTHONPATH=tests/stubs python3 -c "import gui, source, streaming"
```

Notes:
- These stubs are only for local testing and do NOT implement Kodi functionality.
- Do NOT include `tests/stubs` in the final addon package for Kodi; it may conflict with real Kodi modules.

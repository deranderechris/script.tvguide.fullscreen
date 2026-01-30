@echo off
echo Wende Patch auf gui.py an...

REM Backup erstellen
copy gui.py gui_backup.py >nul

REM Dialog().ok Patch
powershell -Command "(Get-Content gui.py) -replace 'xbmcgui\.Dialog\(\)\.ok\((.*?)\,(.*?)\,(.*?)\)', 'msg = f\"{strings(LOAD_ERROR_LINE1)}\n{strings(CONFIGURATION_ERROR_LINE2)}\"\r\nxbmcgui.Dialog().ok(strings(LOAD_ERROR_TITLE), msg)' | Set-Content gui.py"

REM CATEGORIES Patch
powershell -Command "(Get-Content gui.py) -replace 'COMMAND_ACTIONS

\[""CATEGORIES""\]

', 'COMMAND_ACTIONS.get(\"CATEGORIES\", [])' | Set-Content gui.py"

echo.
echo Patch abgeschlossen.
echo Backup wurde erstellt: gui_backup.py
pause

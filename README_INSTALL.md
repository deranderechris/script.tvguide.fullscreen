Installation (Kodi)
-------------------

Kurz: Dieses ZIP ist ein Kodi‑Addon‑Package, das du in Kodi installieren kannst.

1) Prüfe deine Kodi‑Version
- Kodi 19+ verwendet Python 3 — diese Version wurde auf Python 3 portiert.
- Ältere Kodi‑Versionen (z. B. Kodi 18) benötigen Python 2 und sind mit dieser Portierung nicht kompatibel.

2) Lokale Installation
- Lade das Addon‑ZIP (`script.tvguide.fullscreen.addon.zip`) herunter.
- In Kodi: Einstellungen → Addons → Aus ZIP‑Datei installieren → die ZIP wählen.

3) Paketieren / Release
- Das ZIP wurde aus dem Branch `remove-stubs` erzeugt und liegt im Archiv `backups/script.tvguide.fullscreen.addon.zip` im Repo.

4) Hinweise
- Die Test‑Stubs (`tests/stubs`) sind aus dem Release‑ZIP entfernt worden.
- Die Lizenzdatei `LICENSE.txt` ist im Paket enthalten (GPL v2).
- Wenn du das Addon auf einem echten Kodi testen willst, lade das ZIP auf das Zielgerät und installiere es dort.

5) Troubleshooting
- Fehlende Kodi‑Module beim lokalen Import testen: benutze die Stubs (nur für lokale Tests), siehe `backups/stubs_backup.tar.gz`.
- Wenn Kodi bei Start Fehler anzeigt, prüfe `kodi.log` auf fehlende Abhängigkeiten.

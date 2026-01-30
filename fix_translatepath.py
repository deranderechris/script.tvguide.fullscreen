import os
import re

def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. xbmc.translatePath → xbmcvfs.translatePath
    content = re.sub(
        r"xbmc\.translatePath",
        "xbmcvfs.translatePath",
        content
    )

    # 2. import xbmcvfs hinzufügen, falls nicht vorhanden
    if "xbmcvfs" in content and "import xbmcvfs" not in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("import xbmc") or line.startswith("from xbmc"):
                lines.insert(i + 1, "import xbmcvfs")
                break
        content = "\n".join(lines)

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✔ Gefixt: {path}")
    else:
        print(f"OK: {path}")

def walk():
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                fix_file(os.path.join(root, file))

if __name__ == "__main__":
    walk()
    print("\nFertig. Alle translatePath‑Altlasten wurden korrigiert.")


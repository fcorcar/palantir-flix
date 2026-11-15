"""Construye el repositorio de Kodi a partir de los .zip de la raíz del repo de GitHub.

Uso: python build_repo.py <carpeta_con_zips> <carpeta_salida>

- Lee el addon.xml de cada zip (id y versión). Si hay varios zips del mismo addon, usa la versión más alta.
- Copia cada uno a <salida>/<id>/<id>-<version>.zip, que es la ruta que exige Kodi.
- Genera addons.xml, addons.xml.md5 y un index.html para poder añadir la web como fuente en Kodi.
- Deja también en la raíz el zip del repositorio, para "Instalar desde un archivo zip".
"""
import hashlib
import html
import os
import re
import shutil
import sys
import zipfile


def version_key(v):
    parts = []
    for p in re.split(r"[.\-+~]", v):
        parts.append((0, int(p), "") if p.isdigit() else (1, 0, p))
    return parts


def read_addon(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.count("/") == 1 and n.endswith("/addon.xml")]
        if not names:
            return None
        xml = z.read(names[0]).decode("utf-8-sig")
    m = re.search(r'<addon\b[^>]*?\bid="([^"]+)"', xml)
    v = re.search(r'<addon\b[^>]*?\bversion="([^"]+)"', xml)
    if not m or not v:
        return None
    body = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", xml).strip()
    return m.group(1), v.group(1), body


def main(src, out):
    found = {}
    for name in sorted(os.listdir(src)):
        if not name.lower().endswith(".zip"):
            continue
        info = read_addon(os.path.join(src, name))
        if not info:
            print("Ignorado (sin addon.xml):", name)
            continue
        aid, ver, body = info
        if aid not in found or version_key(ver) > version_key(found[aid][0]):
            found[aid] = (ver, body, name)

    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    entries, root_links = [], []
    for aid in sorted(found):
        ver, body, name = found[aid]
        os.makedirs(os.path.join(out, aid))
        dest = "%s-%s.zip" % (aid, ver)
        shutil.copyfile(os.path.join(src, name), os.path.join(out, aid, dest))
        if aid.startswith("repository."):
            shutil.copyfile(os.path.join(src, name), os.path.join(out, dest))
            root_links.append(dest)
        entries.append(body)
        print("OK %s %s  (%s)" % (aid, ver, name))
        with open(os.path.join(out, aid, "index.html"), "w", encoding="utf-8") as f:
            f.write('<!DOCTYPE html>\n<html><body>\n<a href="%s">%s</a><br>\n</body></html>\n' % (dest, dest))

    addons = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n' + "\n".join(entries) + "\n</addons>\n"
    with open(os.path.join(out, "addons.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(addons)
    with open(os.path.join(out, "addons.xml.md5"), "w", encoding="utf-8") as f:
        f.write(hashlib.md5(addons.encode("utf-8")).hexdigest())

    links = root_links + ["%s/" % a for a in sorted(found)]
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html><body>\n")
        for link in links:
            f.write('<a href="%s">%s</a><br>\n' % (html.escape(link), html.escape(link)))
        f.write("</body></html>\n")
    open(os.path.join(out, ".nojekyll"), "w").close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "_site")

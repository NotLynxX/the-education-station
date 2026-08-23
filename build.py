#!/usr/bin/env python3
"""
The Education Station+ - builder
-----------------------------
Run this any time you add or remove something in /html/ or an icon in /Icons/.

What it does:
  1. Looks in /html/ for every playable page it can find:
       - a subfolder containing index.html (as before)
       - a subfolder that has SOME .html file but not index.html - the
         first one found (alphabetically) is used as the entry point
       - a loose .html file sitting directly in /html/ (no subfolder at all)
  2. Adds any new ones to resources.json with a default name (auto-titled
     from the folder/file name) and, if it finds an image in /Icons/ with
     the exact same name (e.g. Icons/my-resource.png for html/my-resource/
     or html/my-resource.html), links it automatically.
  3. Removes entries for folders/files that no longer exist.
  4. Rewrites the resource list and icon list inside index.html to match.

Your own edits to resources.json (custom names/descriptions/icons) are
always kept - this script only fills in NEW entries, it never overwrites
existing ones (though it does keep the "path" field in sync if you rename
the actual HTML file inside a folder).

If you're upgrading from an older version of this project, this script
automatically picks up your existing data the first time it runs, even if
it was previously saved under a different filename (games.json or
library.json) - nothing gets reset to empty.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(ROOT, "html")
ICONS_DIR = os.path.join(ROOT, "Icons")
LIBRARY_JSON = os.path.join(ROOT, "resources.json")
LEGACY_LIBRARY_JSON_NAMES = ["games.json", "library.json"]
FEATURED_JSON = os.path.join(ROOT, "featured.json")
INDEX_HTML = os.path.join(ROOT, "index.html")

ICON_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"]


def migrate_legacy_library_file():
    """One-time auto-heal: if resources.json doesn't exist yet but an older
    project used a different filename for this same data, adopt it instead
    of silently starting over empty. Never overwrites resources.json if it
    already exists."""
    if os.path.exists(LIBRARY_JSON):
        return
    for legacy_name in LEGACY_LIBRARY_JSON_NAMES:
        legacy_path = os.path.join(ROOT, legacy_name)
        if os.path.exists(legacy_path):
            with open(legacy_path, "r", encoding="utf-8") as f:
                data = f.read()
            with open(LIBRARY_JSON, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"Found your existing {legacy_name} - copied it to resources.json (one-time upgrade, nothing was lost).")
            return


def load_library():
    migrate_legacy_library_file()
    if os.path.exists(LIBRARY_JSON):
        with open(LIBRARY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_library(library):
    with open(LIBRARY_JSON, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_featured():
    if os.path.exists(FEATURED_JSON):
        with open(FEATURED_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_featured(featured):
    with open(FEATURED_JSON, "w", encoding="utf-8") as f:
        json.dump(featured, f, indent=2, ensure_ascii=False)
        f.write("\n")


def find_icon_for(key):
    if not os.path.isdir(ICONS_DIR):
        return ""
    # icon files are flat (no subfolders), so a compound key like
    # "offline/some-resource" is looked up as "offline-some-resource.png"
    flat_key = key.replace("/", "-")
    for ext in ICON_EXTS:
        candidate = f"{flat_key}{ext}"
        if os.path.exists(os.path.join(ICONS_DIR, candidate)):
            return f"Icons/{candidate}"
    return ""


def list_resource_items():
    """Returns every playable HTML page found under /html/, as a list of
    {folder, path} dicts. 'folder' is the unique key used everywhere else
    (resources.json, overrides, favorites, etc). 'path' is the relative link
    to actually open.

    Rules, checked in order for each subfolder of /html/:
      - has index.html            -> one resource, using index.html
      - has exactly one .html file -> one resource, using that file
      - has multiple .html files   -> EACH file becomes its own resource,
                                       keyed as "<subfolder>/<filename>"
                                       (e.g. html/offline/tetris.html
                                       becomes the resource "offline/tetris")
    A loose .html file directly inside /html/ (no subfolder) is always
    its own resource, keyed by its filename.
    """
    items = []
    if not os.path.isdir(HTML_DIR):
        return items

    for name in sorted(os.listdir(HTML_DIR)):
        full = os.path.join(HTML_DIR, name)

        if os.path.isdir(full):
            html_files = sorted(
                n for n in os.listdir(full)
                if n.lower().endswith(".html") and os.path.isfile(os.path.join(full, n))
            )
            if not html_files:
                continue

            if "index.html" in html_files:
                items.append({"folder": name, "path": f"html/{name}/index.html"})
            elif len(html_files) == 1:
                items.append({"folder": name, "path": f"html/{name}/{html_files[0]}"})
            else:
                for hf in html_files:
                    key = f"{name}/{os.path.splitext(hf)[0]}"
                    items.append({"folder": key, "path": f"html/{name}/{hf}"})

        elif name.lower().endswith(".html"):
            key = os.path.splitext(name)[0]
            items.append({"folder": key, "path": f"html/{name}"})

    return items


def list_icon_files():
    if not os.path.isdir(ICONS_DIR):
        return []
    out = []
    for name in sorted(os.listdir(ICONS_DIR)):
        if os.path.splitext(name)[1].lower() in ICON_EXTS:
            out.append(f"Icons/{name}")
    return out


def titleize(folder):
    # for compound keys like "offline/tetris", title only the last part
    base = folder.rsplit("/", 1)[-1]
    return base.replace("-", " ").replace("_", " ").strip().title()


def sync_library():
    library = load_library()
    items = list_resource_items()
    found_map = {it["folder"]: it["path"] for it in items}
    found = set(found_map.keys())

    # drop entries whose folder/file no longer exists
    library = [g for g in library if g["folder"] in found]
    known = {g["folder"] for g in library}

    # keep the "path" field in sync for existing entries, in case the
    # actual entry HTML file inside a folder changed (e.g. index.html
    # was renamed to play.html). Also auto-assign an icon to any existing
    # entry that doesn't have one set yet, in case a matching image got
    # added to /Icons/ after the resource was first added - this never
    # touches an icon that's already set, whether that was auto-assigned
    # earlier or picked by hand in edit mode.
    for g in library:
        g["path"] = found_map[g["folder"]]
        if not g.get("icon"):
            found_icon = find_icon_for(g["folder"])
            if found_icon:
                g["icon"] = found_icon

    # add new items, preserving the order they were found in
    next_num = len(library) + 1
    for it in items:
        if it["folder"] not in known:
            library.append({
                "folder": it["folder"],
                "name": titleize(it["folder"]),
                "desc": "",
                "tag": f"{next_num:02d}",
                "icon": find_icon_for(it["folder"]),
                "path": it["path"],
                "download": ""
            })
            next_num += 1

    save_library(library)
    return library


def sync_featured(library):
    known = {g["folder"] for g in library}
    featured = load_featured()
    # drop entries whose resource no longer exists - never auto-adds anything,
    # featured picks are curated by hand or via the site's edit mode
    featured = [f for f in featured if f.get("folder") in known]
    save_featured(featured)
    return featured


def js_string(s):
    return json.dumps(s if s is not None else "")


def build_resources_js(library):
    lines = ["  const resources = ["]
    for g in library:
        path = g.get("path") or f"html/{g.get('folder','')}/index.html"
        lines.append("    {")
        lines.append(f"      name: {js_string(g.get('name',''))},")
        lines.append(f"      folder: {js_string(g.get('folder',''))},")
        lines.append(f"      tag: {js_string(g.get('tag',''))},")
        lines.append(f"      desc: {js_string(g.get('desc',''))},")
        lines.append(f"      icon: {js_string(g.get('icon',''))},")
        lines.append(f"      path: {js_string(path)},")
        lines.append(f"      download: {js_string(g.get('download',''))}")
        lines.append("    },")
    lines.append("  ];")
    return "\n".join(lines)


def build_icons_js(icon_files):
    arr = ", ".join(js_string(i) for i in icon_files)
    return f"  const availableIcons = [{arr}];"


def build_featured_js(featured):
    lines = ["  const featuredBase = ["]
    for f in featured:
        lines.append("    {")
        lines.append(f"      folder: {js_string(f.get('folder',''))},")
        lines.append(f"      name: {js_string(f.get('name',''))},")
        lines.append(f"      icon: {js_string(f.get('icon',''))}")
        lines.append("    },")
    lines.append("  ];")
    return "\n".join(lines)


def replace_between(text, start_marker, end_marker, new_block):
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(text):
        raise RuntimeError(f"Could not find markers {start_marker} ... {end_marker} in index.html")
    replacement = f"{start_marker}\n{new_block}\n  {end_marker}"
    return pattern.sub(replacement, text, count=1)


def main():
    library = sync_library()
    featured = sync_featured(library)
    icon_files = list_icon_files()

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    html = replace_between(html, "/* AUTO-RESOURCES-START */", "/* AUTO-RESOURCES-END */", build_resources_js(library))
    html = replace_between(html, "/* AUTO-ICONS-START */", "/* AUTO-ICONS-END */", build_icons_js(icon_files))
    html = replace_between(html, "/* AUTO-FEATURED-START */", "/* AUTO-FEATURED-END */", build_featured_js(featured))

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Synced {len(library)} resource(s):")
    for g in library:
        print(f"  - {g['name']}  ({g['path']})  icon: {g['icon'] or '(none set - will show a letter instead)'}")
    print(f"\nFeatured carousel: {len(featured)} resource(s) - edit featured.json or use the site's edit mode to change it.")
    print("index.html has been updated. Open it in your browser to see the changes.")


if __name__ == "__main__":
    main()

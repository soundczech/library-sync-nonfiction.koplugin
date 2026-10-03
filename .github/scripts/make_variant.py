#!/usr/bin/env python3
"""Build an independent second copy ("variant") of the Library Sync KOReader plugin.

Usage: make_variant.py <upstream-checkout> <output-plugin-dir>

Two copies of the same plugin collide inside KOReader unless every identifier
they register is different. This script copies an upstream checkout and
renames those identifiers:

  * settings / history / manifest / path-rules file names
  * the main-menu entry key, gesture (Dispatcher) action ids and their events
  * the long-press file-dialog button id
  * the Lua module names (KOReader caches modules by name across plugins, so
    an un-renamed "grimmory_updater" would be shared and could update the
    wrong copy)
  * the built-in updater's GitHub repo and release-asset name
  * the visible menu labels

It then checks that nothing the variant registers is still shared with the
original, and exits non-zero if so. A failed run publishes nothing.

Configuration comes from environment variables:
  VARIANT_OWNER  GitHub user that owns the variant repo
  VARIANT_REPO   variant repo name; also the plugin folder name, so it must
                 end in ".koplugin"
  VARIANT_LABEL  text shown in menus, e.g. "Nonfiction"
  VARIANT_ID     short lowercase id used inside identifiers, e.g. "nf"
"""
import os
import re
import shutil
import sys
from pathlib import Path

UPSTREAM_DIR = "library-sync.koplugin"
SKIP_COPY = {".git", ".github", "tests"}
SKIP_MODULE_DIRS = {"examples"}
KEEP_MODULE_NAMES = {"main", "_meta"}


def die(msg):
    print(f"make_variant: ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def lua_files(root):
    return sorted(p for p in root.rglob("*.lua") if not (set(p.relative_to(root).parts[:-1]) & SKIP_MODULE_DIRS))


def registered_ids(root):
    """Everything a plugin copy registers globally with KOReader or on disk."""
    patterns = {
        "gesture action": r'registerAction\(\s*"([^"]+)"',
        "file dialog button": r'addFileDialogButtons\(\s*"([^"]+)"',
        "menu key": r'menu_items\.(\w+)\s*=',
        "event": r'\bevent\s*=\s*"([^"]+)"',
        "data file": r'(?:settingsPath|dataPath|androidLegacyPath)\(\s*"([^"]+)"\s*\)',
        "temp file": r'"[^"]*?([\w.-]+_update\.zip)"',
    }
    ids = set()
    for path in lua_files(root):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        top_level = len(rel.parts) == 1
        if top_level and rel.stem in KEEP_MODULE_NAMES:
            for m in re.finditer(r'^\s*name\s*=\s*"([^"]+)"', text, re.M):
                ids.add(("plugin name", m.group(1)))
        else:
            # Lua module name as require() sees it
            ids.add(("module", rel.with_suffix("").as_posix()))
        for kind, pat in patterns.items():
            for m in re.finditer(pat, text):
                ids.add((kind, m.group(1)))
    return ids


def main():
    if len(sys.argv) != 3:
        die("usage: make_variant.py <upstream-checkout> <output-plugin-dir>")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    owner = os.environ.get("VARIANT_OWNER", "")
    repo = os.environ.get("VARIANT_REPO", "")
    label = os.environ.get("VARIANT_LABEL", "Nonfiction")
    vid = os.environ.get("VARIANT_ID", "nf")

    if not re.fullmatch(r"[A-Za-z0-9-]+", owner):
        die("VARIANT_OWNER must be a GitHub user name")
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.koplugin", repo):
        die('VARIANT_REPO (the repository name) must end in ".koplugin"')
    if repo.lower() in (UPSTREAM_DIR, "grimmory-sync.koplugin"):
        die("the variant repo must not be named like the original plugin")
    if not re.fullmatch(r"[a-z][a-z0-9]{0,11}", vid):
        die("VARIANT_ID must be 1-12 lowercase letters/digits, starting with a letter")
    if not re.fullmatch(r"[A-Za-z0-9 _-]{1,24}", label):
        die("VARIANT_LABEL may only contain letters, digits, spaces, - and _")
    if not (src / "main.lua").is_file() or not (src / "_meta.lua").is_file():
        die(f"{src} does not look like a KOReader plugin")

    vid_cap = vid.upper()
    vid_camel = vid.capitalize()

    # 1. Copy the plugin.
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if n in SKIP_COPY])

    # 2. Rename Lua modules so require() can never hand this copy the
    #    original's cached module (or the other way round).
    file_modules, dir_modules = [], []
    for p in sorted(dst.iterdir()):
        if p.is_file() and p.suffix == ".lua" and p.stem not in KEEP_MODULE_NAMES:
            p.rename(p.with_name(f"{p.stem}_{vid}.lua"))
            file_modules.append(p.stem)
        elif p.is_dir() and p.name not in SKIP_MODULE_DIRS and any(p.rglob("*.lua")):
            p.rename(p.with_name(f"{p.name}_{vid}"))
            dir_modules.append(p.name)

    files = lua_files(dst)
    texts = {p: p.read_text(encoding="utf-8") for p in files}
    all_text = "\n".join(texts.values())

    # Events that this plugin both registers and handles itself.
    events = sorted(
        e for e in set(re.findall(r'\bevent\s*=\s*"(\w+)"', all_text))
        if re.search(rf"[:.]on{re.escape(e)}\b", all_text)
    )

    req = r'(\brequire\b\s*[(,]?\s*["\'])'
    rules = []  # (description, compiled regex, replacement, required?)

    def rule(desc, pattern, repl, required=True):
        rules.append((desc, re.compile(pattern), repl, required))

    for name in file_modules:
        rule(f"module {name}", req + re.escape(name) + r'(?=["\'])', rf"\g<1>{name}_{vid}")
    for name in dir_modules:
        rule(f"module dir {name}", req + re.escape(name) + r"(?=[/.])", rf"\g<1>{name}_{vid}")

    rule("settings/data file names and action ids",
         r"\b(library_sync|grimmory_sync|booklore_sync)_(?=[a-z])", rf"\g<1>_{vid}_")
    rule("main menu key", r"\bgrimmory_sync\b", f"grimmory_sync_{vid}")
    rule("refresh action / button ids", r"\bgrimmory_refresh_", f"grimmory_{vid}_refresh_")
    rule("plugin name", r'"grimmorysync"', f'"grimmorysync{vid}"')
    for e in events:
        rule(f"event {e}", rf"\b(on)?{re.escape(e)}\b", rf"\g<1>{e}{vid_camel}")
    rule("updater owner", r'(GITHUB_OWNER\s*=\s*)"[^"]*"', rf'\g<1>"{owner}"')
    rule("updater repo", r'(GITHUB_REPO\s*=\s*)"[^"]*"', rf'\g<1>"{repo}"')
    rule("plugin folder / release asset name", re.escape(UPSTREAM_DIR), repo)
    rule("menu label", r'"Library Sync"', f'"Library Sync ({label})"')
    rule("action titles", r'"Library Sync: ', f'"Library Sync ({label}): ', required=False)
    rule("file dialog button label", r'"Refresh server metadata"',
         f'"Refresh server metadata ({label})"', required=False)
    rule("log tag", r"\[GrimmorySync\]", f"[GrimmorySync{vid_cap}]", required=False)

    hits = {desc: 0 for desc, *_ in rules}
    for path in files:
        text = texts[path]
        for desc, rx, repl, _required in rules:
            text, n = rx.subn(repl, text)
            hits[desc] += n
        path.write_text(text, encoding="utf-8")

    for desc, _rx, _repl, required in rules:
        print(f"  {hits[desc]:4d}  {desc}")
        if required and hits[desc] == 0:
            die(f'rule "{desc}" matched nothing - upstream changed, the script needs updating')
    if not events:
        die("no Dispatcher events found - upstream changed, the script needs updating")

    # 3. Refuse to ship anything that would still collide with the original.
    shared = registered_ids(src) & registered_ids(dst)
    if shared:
        for kind, value in sorted(shared):
            print(f"  still shared with the original: {kind} {value}", file=sys.stderr)
        die("the variant would collide with the original plugin")

    # 4. Say what this is, in the README that Storefront displays.
    readme = dst / "README.md"
    notice = (
        f"> **Library Sync ({label})** - an automatically generated second copy of\n"
        f"> [Library Sync](https://github.com/komadorirobin/{UPSTREAM_DIR}) by komadorirobin,\n"
        f"> renamed so it can be installed next to the original with its own settings\n"
        f"> and book folder. Unless you need two instances, install the original.\n"
        f"> Please do not report problems with this copy to the upstream author.\n\n"
    )
    body = readme.read_text(encoding="utf-8") if readme.exists() else ""
    readme.write_text(notice + body, encoding="utf-8")

    print(f"make_variant: built {dst} ({len(files)} Lua files)")


if __name__ == "__main__":
    main()

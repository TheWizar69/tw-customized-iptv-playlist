#!/usr/bin/env python3
"""
Refresh selected IPTV channel entries from the OTV source playlist.

The names in channels.txt MUST be the exact source names.
For each selected name, the COMPLETE source entry is copied into
thewizard.m3u unchanged: #EXTINF metadata, logo, group, URL, etc.

If a selected source channel is temporarily missing, the existing entry
with the same name is retained rather than deleting it.
"""

from pathlib import Path
from urllib.request import Request, urlopen
import re
import sys

SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "johirxofficial/otv-auto-updated-playlist/main/otv.m3u"
)
CHANNELS_FILE = Path("channels.txt")
PLAYLIST_FILE = Path("thewizard.m3u")


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 GitHub Actions"})
    with urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def get_name(extinf):
    match = re.search(r'tvg-name="([^"]*)"', extinf, re.I)
    if match:
        return match.group(1).strip()
    return extinf.rsplit(",", 1)[-1].strip() if "," in extinf else ""


def parse_m3u(text):
    lines = [line.rstrip("\r") for line in text.splitlines()]
    entries = []
    extinf = None
    following = []

    for line in lines:
        if not line.strip():
            continue

        if line.startswith("#EXTINF:"):
            if extinf is not None:
                entries.append((get_name(extinf), extinf, following))
            extinf = line
            following = []
        elif extinf is not None:
            following.append(line)

    if extinf is not None:
        entries.append((get_name(extinf), extinf, following))

    return entries


def norm(value):
    return " ".join(value.casefold().split())


def main():
    if not CHANNELS_FILE.exists():
        sys.exit("ERROR: channels.txt not found.")
    if not PLAYLIST_FILE.exists():
        sys.exit("ERROR: thewizard.m3u not found.")

    selected = [
        line.strip()
        for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    source = parse_m3u(fetch(SOURCE_URL))
    existing = parse_m3u(PLAYLIST_FILE.read_text(encoding="utf-8-sig"))

    source_map = {norm(name): entry for name, *entry in source}
    existing_map = {norm(name): entry for name, *entry in existing}

    output = []
    updated = []
    kept = []
    missing = []

    for wanted in selected:
        key = norm(wanted)

        if key in source_map:
            name, extinf, rest = source_map[key]
            output.append((name, extinf, rest))
            updated.append(wanted)
        elif key in existing_map:
            name, extinf, rest = existing_map[key]
            output.append((name, extinf, rest))
            kept.append(wanted)
        else:
            missing.append(wanted)

    header = """#EXTM3U
#=======================================
# Name: TheWizard Customized IPTV Playlist
#=======================================
"""

    blocks = ["\n".join([extinf] + rest) for _, extinf, rest in output]
    PLAYLIST_FILE.write_text(
        header + "\n" + "\n\n".join(blocks) + "\n",
        encoding="utf-8"
    )

    print(f"Selected: {len(selected)}")
    print(f"Updated from source: {len(updated)}")
    for x in updated:
        print(f"  UPDATED: {x}")

    if kept:
        print(f"Source missing; existing entry kept: {len(kept)}")
        for x in kept:
            print(f"  KEPT: {x}")

    if missing:
        print(f"Never found: {len(missing)}")
        for x in missing:
            print(f"  MISSING: {x}")


if __name__ == "__main__":
    main()

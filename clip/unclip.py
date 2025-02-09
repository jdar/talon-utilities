#!/usr/bin/env python3
# talon-utilities/clip/unclip.py
"""
File: talon-utilities/clip/unclip.py

Description:
    Retrieves data from the system clipboard (where feasible) or from the
    fallback file if no functional clipboard mechanism is detected.
    The data is then emitted to STDOUT in the faint hope that it’s still
    useful to you.

Authors:
    - Matt Heck, Hard Problems Group, LLC
    - R. Talon  (Yes, I'll also take the blame if you read absolute nonsense.)

License: MIT
"""

import sys
import os
import subprocess
import argparse
from typing import Optional
from shutil import which as shutil_which

FALLBACK_CLIP_FILE: str = "/tmp/clipboard.dat"

def which(cmd: str) -> Optional[str]:
    """
    Returns the path to 'cmd' if found in PATH, otherwise None.

    (Again, let's see if your system is any better at
    finding commands than it was ten seconds ago.)
    """
    return shutil_which(cmd)

def is_wayland_session() -> bool:
    """
    Check if environment variables suggest Wayland is in play.

    (If you see WAYLAND_DISPLAY, prepare for wl-paste madness.)
    """
    return bool(os.environ.get("WAYLAND_DISPLAY"))

def is_x11_session() -> bool:
    """
    Check if environment variables suggest X11 is in play.

    (Because sometimes the old ways remain with us, for better or worse.)
    """
    return bool(os.environ.get("DISPLAY"))

def read_from_fallback(verbose: bool=False) -> str:
    """
    Retrieve data from the fallback file. This is for those
    bleak TTY times or when nothing else works.

    (At least /tmp/clipboard.dat won't vanish without warning. Probably.)
    """
    if not os.path.exists(FALLBACK_CLIP_FILE):
        if verbose:
            print(f"[ERROR] Fallback file {FALLBACK_CLIP_FILE} does not exist.")
        return ""
    try:
        with open(FALLBACK_CLIP_FILE, "r", encoding="utf-8") as f:
            data = f.read()
        if verbose:
            print(f"[INFO] Read fallback data from {FALLBACK_CLIP_FILE}")
        return data
    except Exception as e:
        if verbose:
            print(f"[ERROR] Could not read from fallback file: {e}")
        return ""

def read_with_xclip(verbose: bool=False) -> str:
    """
    Read data from the clipboard using xclip.

    (Let's hope xclip plays nice. It often does, unless it doesn’t.)
    """
    try:
        p = subprocess.Popen(["xclip", "-selection", "clipboard", "-o"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"xclip returned code {p.returncode}: {err.decode('utf-8','ignore')}")
        data = out.decode("utf-8", "ignore")
        if verbose:
            print("[INFO] Data successfully read using xclip.")
        return data
    except Exception as e:
        if verbose:
            print(f"[WARNING] xclip read failed: {e}")
        return ""

def read_with_xsel(verbose: bool=False) -> str:
    """
    Read data from the clipboard using xsel.

    (xsel: the other X11 horse. Will it remain stable today?)
    """
    try:
        p = subprocess.Popen(["xsel", "--clipboard", "--output"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"xsel returned code {p.returncode}: {err.decode('utf-8','ignore')}")
        data = out.decode("utf-8", "ignore")
        if verbose:
            print("[INFO] Data successfully read using xsel.")
        return data
    except Exception as e:
        if verbose:
            print(f"[WARNING] xsel read failed: {e}")
        return ""

def read_with_wlcopy(verbose: bool=False) -> str:
    """
    Read data from the Wayland clipboard using wl-paste 
    (the sibling command to wl-copy).

    (It’s ironically named 'wl-paste,' not 'wl-copy.' 
    The naming continues to amuse me almost as much as it confuses you.)
    """
    wl_paste_path = which("wl-paste")
    if not wl_paste_path:
        if verbose:
            print("[WARNING] 'wl-paste' not found in PATH.")
        return ""
    try:
        p = subprocess.Popen([wl_paste_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f"wl-paste returned code {p.returncode}: {err.decode('utf-8','ignore')}")
        data = out.decode("utf-8", "ignore")
        if verbose:
            print("[INFO] Data successfully read using wl-paste.")
        return data
    except Exception as e:
        if verbose:
            print(f"[WARNING] wl-paste read failed: {e}")
        return ""

def detect_and_read(verbose: bool=False) -> str:
    """
    Detect environment and attempt to read from whichever clipboard tool
    might still function. If all else fails, read fallback.

    (One tool fails, you move to the next. Resilience is key in a system
    designed to betray you at the worst times.)
    """
    running_wayland: bool = is_wayland_session()
    running_x11: bool = is_x11_session()
    is_tty_only: bool = not (running_wayland or running_x11)

    if verbose:
        if running_wayland:
            print("[INFO] Detected Wayland session.")
        elif running_x11:
            print("[INFO] Detected X11 session.")
        else:
            print("[INFO] No GUI session detected. Must resort to fallback or prayer.")

    # Wayland attempt
    if running_wayland:
        data: str = read_with_wlcopy(verbose=verbose)
        if data:
            return data

        if which("xclip"):
            data = read_with_xclip(verbose=verbose)
            if data:
                return data

        if which("xsel"):
            data = read_with_xsel(verbose=verbose)
            if data:
                return data

        return read_from_fallback(verbose=verbose)

    # X11 attempt
    if running_x11:
        if which("xclip"):
            data = read_with_xclip(verbose=verbose)
            if data:
                return data

        if which("xsel"):
            data = read_with_xsel(verbose=verbose)
            if data:
                return data

        return read_from_fallback(verbose=verbose)

    # TTY fallback
    if is_tty_only:
        return read_from_fallback(verbose=verbose)

    # Unexpected scenario
    return read_from_fallback(verbose=verbose)

def main() -> None:
    """
    Main entrypoint for unclip.py.

    (A final chance for you to see what's in that ephemeral 
    'clipboard' you trusted. Let’s hope it was worth it.)
    """
    parser = argparse.ArgumentParser(
        description="Reads data from system clipboard or fallback. For when you want to see if it survived."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output. Because sometimes we crave more discouraging details."
    )

    args = parser.parse_args()

    data: str = detect_and_read(verbose=args.verbose)
    if not data and args.verbose:
        print("[WARNING] Clipboard/fallback is empty or could not be read. Not my fault, obviously.")

    sys.stdout.write(data)

if __name__ == "__main__":
    main()

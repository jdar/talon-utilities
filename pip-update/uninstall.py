#!/usr/bin/env python3
# talon-utilities/pip-update/uninstall.py
"""
Uninstalls the pip-update utility (because removing a script should be at least
as thorough as installing it, right?).

Author(s):
Matt Heck, President, Hard Problems Group, LLC.
R. Talon

License Reference: See LICENSE.txt in parent directory (the usual disclaimers apply).

Usage:
    python3 uninstall.py

Description:
    This script attempts to remove pip-update from either the system-wide path
    (if installed as root) or a local bin directory (if installed as a normal user).
    It also deletes the corresponding man page, if found, and warns if the operation
    fails in any way.

Environment:
    - Ubuntu 22+, Fedora 41, RHEL 9.5
    - Must be run with root privileges to remove from system directories.
    - Otherwise, attempts to remove from user-local paths.
"""

import os
import sys
import stat
import shutil
from typing import Optional

def find_pip_update_executable() -> Optional[str]:
    """
    Searches a few common locations (including /usr/local/bin and user-local bin directories)
    for a pip-update executable. (Let's cross our fingers that the user hasn’t hidden it.)
    
    Returns:
        The full path to the pip-update binary if found, else None.
    """
    # If we're root, we assume system-wide install:
    if os.geteuid() == 0:
        candidates = [
            "/usr/local/bin/pip-update",
            "/usr/bin/pip-update"  # might as well check
        ]
    else:
        # user-level possibilities
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "bin", "pip-update"),
            os.path.join(home, ".bin", "pip-update"),
            os.path.join(home, ".local", "bin", "pip-update"),
            os.path.join(home, ".local", ".bin", "pip-update")
        ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None

def find_man_page() -> Optional[str]:
    """
    Attempts to locate the pip-update man page. (We only remove it if we find it.)
    
    Returns:
        The full path to the man page if found, else None.
    """
    # system-wide man page location:
    if os.geteuid() == 0:
        candidates = [
            "/usr/local/share/man/man1/pip-update.1",
            "/usr/share/man/man1/pip-update.1",
        ]
    else:
        # user might have a local man directory
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".local", "share", "man", "man1", "pip-update.1"),
        ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def remove_file_if_exists(filepath: str) -> bool:
    """
    Safely remove a file if it exists. (We won't weep if it's missing.)

    Args:
        filepath: The full path of the file to remove.
    Returns:
        True if successfully removed, False if the file didn't exist or removal failed.
    """
    if not os.path.exists(filepath):
        return False
    try:
        os.remove(filepath)
        return True
    except Exception as e:
        print(f"Error removing {filepath}: {e}")
        return False

def main() -> None:
    """
    Main entry point for the uninstaller. (Because installation wasn't enough.)
    
    Steps:
    1. Determine if removing system-wide or user-local pip-update.
    2. Remove the binary if found.
    3. Remove the man page if found.
    4. Warn if anything fails or nothing is found.
    """
    print("Uninstalling pip-update...")

    exe_path = find_pip_update_executable()
    if exe_path:
        print(f"Found pip-update at: {exe_path}")
        if remove_file_if_exists(exe_path):
            print(f"Removed: {exe_path}")
        else:
            print(f"Failed to remove {exe_path}. Check permissions or file state.")
    else:
        print("No pip-update executable found in expected locations.")

    man_path = find_man_page()
    if man_path:
        print(f"Found pip-update man page at: {man_path}")
        if remove_file_if_exists(man_path):
            print("Removed man page.")
            # Attempt to update man database if root
            if os.geteuid() == 0:
                try:
                    os.system("mandb >/dev/null 2>&1")
                except Exception:
                    pass
        else:
            print(f"Failed to remove {man_path}. Check permissions or file state.")
    else:
        print("No pip-update man page found.")

    print("Uninstallation complete. If pip-update still runs, it’s hiding somewhere else.")


if __name__ == "__main__":
    main()


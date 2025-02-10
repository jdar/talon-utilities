#!/usr/bin/env python3
# talon-utilities/uninstall.py
"""
uninstall.py - Thorough uninstaller for Talon Utilities.

This script removes the Talon Utilities (clip/unclip and associated man pages)
from their installed system locations. It targets Ubuntu, RHEL 9.5, and Fedora 41.
It adheres to best system administration practices and is as pessimistic as necessary.

Usage:
    sudo python3 uninstall.py [--bindir BINDIR] [--mandir MANDIR]

Options:
    --bindir   Directory from which executable scripts are removed (default: /usr/local/bin)
    --mandir   Directory from which man pages are removed (default: /usr/local/share/man/man1)

Authors:
    Matt Heck, President, Hard Problems Group, LLC
    R. Talon

License: Refer to the LICENSE file.
"""

import argparse
import os
import sys
import subprocess
from typing import NoReturn

def check_root() -> None:
    """Ensure the uninstaller is run with root privileges."""
    if os.geteuid() != 0:
        print("Error: This uninstaller must be run as root. Try using 'sudo'.", file=sys.stderr)
        sys.exit(1)

def remove_file(filepath: str) -> None:
    """
    Remove a file if it exists.

    Args:
        filepath: The full path to the file to be removed.
    """
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Removed: {filepath}")
        except Exception as e:
            print(f"Error: Unable to remove {filepath}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Warning: {filepath} not found.")

def update_mandb(mandir: str) -> None:
    """
    Update the man page database.

    Args:
        mandir: The directory containing the installed man pages.
    """
    try:
        subprocess.run(["mandb"], check=True)
        print("Man database updated successfully.")
    except subprocess.SubprocessError as e:
        print(f"Warning: Failed to update man database: {e}", file=sys.stderr)

def main() -> NoReturn:
    """Main uninstallation routine."""
    check_root()

    parser = argparse.ArgumentParser(
        description="Thorough uninstaller for Talon Utilities."
    )
    parser.add_argument(
        "--bindir",
        default="/usr/local/bin",
        help="Directory from which executable scripts are removed (default: /usr/local/bin)"
    )
    parser.add_argument(
        "--mandir",
        default="/usr/local/share/man/man1",
        help="Directory from which man pages are removed (default: /usr/local/share/man/man1)"
    )
    args = parser.parse_args()

    bindir = os.path.abspath(args.bindir)
    mandir = os.path.abspath(args.mandir)

    # Files installed by the installer:
    # Executable scripts (without the .py extension)
    script_files = ["clip", "unclip"]
    # Man pages
    manpage_files = ["clip.1", "unclip.1"]

    # Remove scripts from bindir
    for script in script_files:
        script_path = os.path.join(bindir, script)
        remove_file(script_path)

    # Remove man pages from mandir
    for manpage in manpage_files:
        manpage_path = os.path.join(mandir, manpage)
        remove_file(manpage_path)

    # Update the man page database
    update_mandb(mandir)

    print("\nUninstallation complete. All traces of Talon Utilities have been purged.")

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# talon-utilities/install.py
"""
install.py - Thorough installer for Talon Utilities.

This script installs the Talon Utilities (clip/unclip and associated man pages) to
their proper system locations, targeting Ubuntu, RHEL 9.5, and Fedora 41.
It adheres to best system administration practices and is as pessimistic as necessary.

Usage:
    sudo python3 install.py [--bindir BINDIR] [--mandir MANDIR]

Options:
    --bindir   Directory to install executable scripts (default: /usr/local/bin)
    --mandir   Directory to install man pages (default: /usr/local/share/man/man1)

Authors:
    Matt Heck, President, Hard Problems Group, LLC
    R. Talon

License: Refer to the LICENSE file.
"""

import argparse
import os
import shutil
import subprocess
import sys
from typing import NoReturn

def check_root() -> None:
    """Ensure the installer is run with root privileges."""
    if os.geteuid() != 0:
        print("Error: This installer must be run as root. Try using 'sudo'.", file=sys.stderr)
        sys.exit(1)

def check_python_version() -> None:
    """Ensure Python 3.6 or newer is used."""
    if sys.version_info < (3, 6):
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"Error: Python 3.6 or newer is required. Current version: {current_version}", file=sys.stderr)
        print("Please run the installer using an appropriate Python interpreter (e.g. 'python3').", file=sys.stderr)
        sys.exit(1)

def copy_script(src: str, dest_dir: str) -> None:
    """
    Copy a script to the destination directory and remove its .py extension.
    
    Args:
        src: Source path of the script.
        dest_dir: Destination directory.
    """
    if not os.path.isfile(src):
        print(f"Error: Source script '{src}' not found.", file=sys.stderr)
        sys.exit(1)
    
    base = os.path.basename(src)
    # Remove the .py extension
    dest_name = os.path.splitext(base)[0]
    dest_path = os.path.join(dest_dir, dest_name)
    
    try:
        shutil.copy(src, dest_path)
        os.chmod(dest_path, 0o755)
        print(f"Installed script: {dest_path}")
    except Exception as e:
        print(f"Error: Failed to install {src} to {dest_path}: {e}", file=sys.stderr)
        sys.exit(1)

def copy_manpage(src: str, dest_dir: str) -> None:
    """
    Copy a man page to the destination directory.
    
    Args:
        src: Source path of the man page.
        dest_dir: Destination directory.
    """
    if not os.path.isfile(src):
        print(f"Error: Source man page '{src}' not found.", file=sys.stderr)
        sys.exit(1)
    
    dest_path = os.path.join(dest_dir, os.path.basename(src))
    try:
        shutil.copy(src, dest_path)
        print(f"Installed man page: {dest_path}")
    except Exception as e:
        print(f"Error: Failed to install {src} to {dest_path}: {e}", file=sys.stderr)
        sys.exit(1)

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
    """Main installation routine."""
    check_python_version()
    check_root()

    parser = argparse.ArgumentParser(
        description="Thorough installer for Talon Utilities."
    )
    parser.add_argument(
        "--bindir",
        default="/usr/local/bin",
        help="Directory to install executable scripts (default: /usr/local/bin)"
    )
    parser.add_argument(
        "--mandir",
        default="/usr/local/share/man/man1",
        help="Directory to install man pages (default: /usr/local/share/man/man1)"
    )
    args = parser.parse_args()

    bindir = os.path.abspath(args.bindir)
    mandir = os.path.abspath(args.mandir)

    # Ensure target directories exist
    os.makedirs(bindir, exist_ok=True)
    os.makedirs(mandir, exist_ok=True)

    # Define source file locations
    # Assuming the following structure:
    # talon-utilities/
    #    install.py
    #    INSTALL.TXT
    #    README.md
    #    clip/
    #         clip.py, unclip.py, clip.1, unclip.1
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clip")
    scripts = [("clip.py", "clip"), ("unclip.py", "unclip")]
    manpages = [("clip.1", "clip.1"), ("unclip.1", "unclip.1")]

    # Install scripts
    for src_file, _ in scripts:
        src_path = os.path.join(script_dir, src_file)
        copy_script(src_path, bindir)

    # Install man pages
    for src_file, _ in manpages:
        src_path = os.path.join(script_dir, src_file)
        copy_manpage(src_path, mandir)

    # Update the man page database
    update_mandb(mandir)

    print("\nInstallation complete. Enjoy the existential dread of your new utilities.")

if __name__ == "__main__":
    main()

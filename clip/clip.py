#!/usr/bin/env python3
# talon-utilities/clip/clip.py
"""
clip.py - Copy text to the system clipboard from STDIN or file(s).

Authors:
    Matt Heck, President, Hard Problems Group, LLC
    R. Talon

License: Refer to the LICENSE file.

This utility operates in two modes:
1. STDIN Mode (default): If no filename is provided, text is read from standard input.
2. File Mode: If one or more filenames are provided, the contents of the file(s) are read.
   - With exactly one file (and --interactive not specified), the file’s content is copied to the
     clipboard immediately.
   - With multiple files, the --interactive flag is required. In interactive mode, for each file,
     the filename, modification date, and size are displayed; the file’s content is copied to the
     clipboard; then the user is prompted: "Copied. Press SPACE for next file or Q to quit."
     The operation proceeds based on the keystroke.

(No fallback to temporary files is provided; if clipboard copy fails, an error is raised.)
"""

import os
import sys
import subprocess
import shutil
import argparse
import time
import termios
import tty
from typing import Optional, List, NoReturn

def get_clipboard_command(preferred: Optional[str] = None) -> Optional[List[str]]:
    """
    Determine the available clipboard command.

    If a preferred utility is provided, verify its presence; otherwise, choose the most
    appropriate utility based on the environment (favoring Wayland if available).

    Args:
        preferred: Preferred clipboard utility (xclip, xsel, or wl-copy), if any.
    Returns:
        A list representing the command and its arguments if available, else None.
    (Select your clipboard savior; if none is present, we throw in the towel.)
    """
    if preferred:
        if preferred == "xclip" and shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        elif preferred == "xsel" and shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"]
        elif preferred == "wl-copy" and shutil.which("wl-copy"):
            return ["wl-copy"]
        else:
            print(f"Error: Preferred utility '{preferred}' not found in PATH.", file=sys.stderr)
            return None

    # No preferred utility specified; choose based on environment.
    if os.environ.get("WAYLAND_DISPLAY"):
        if shutil.which("wl-copy"):
            return ["wl-copy"]
        elif shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        elif shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"]
        else:
            return None
    elif os.environ.get("DISPLAY"):
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        elif shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"]
        elif shutil.which("wl-copy"):
            return ["wl-copy"]
        else:
            return None
    else:
        return None

def copy_to_system_clipboard(text: str, cmd: Optional[List[str]] = None) -> bool:
    """
    Copy text to the system clipboard using the specified external utility.

    Args:
        text: The text to copy.
        cmd: The command list to use for copying; if None, it is determined automatically.
    Returns:
        True if the clipboard copy was successful, False otherwise.
    (We fail fast if the clipboard doesn't cooperate.)
    """
    if cmd is None:
        cmd = get_clipboard_command()
    if cmd is None:
        return False
    try:
        proc = subprocess.run(cmd, input=text.encode('utf-8'), check=True)
        return proc.returncode == 0
    except subprocess.SubprocessError as e:
        print(f"Error: System clipboard copy failed: {e}", file=sys.stderr)
        return False

def get_installation_instructions() -> str:
    """
    Provide instructions for installing a suitable clipboard utility based on the environment.

    Returns:
        A string with installation instructions.
    (Clear directions so you know which package to install when the clipboard utility is MIA.)
    """
    if os.environ.get("WAYLAND_DISPLAY"):
        return ("Please install 'wl-copy' (e.g., sudo dnf install wl-clipboard or "
                "sudo apt install wl-clipboard) for Wayland.")
    elif os.environ.get("DISPLAY"):
        return ("Please install 'xclip' (e.g., sudo dnf install xclip or "
                "sudo apt install xclip) or 'xsel' for X11.")
    else:
        return "No graphical environment detected. Clipboard functionality requires a GUI environment."

def getch() -> str:
    """
    Read a single character from standard input without echo.

    Returns:
        The character read.
    (A low-level trick to grab a keystroke; no fuss, just a single char.)
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def process_file(filename: str, cmd: List[str]) -> bool:
    """
    Process a single file in interactive mode: display its details, copy its content to the clipboard,
    and prompt the user to continue or quit.

    Args:
        filename: The path to the file.
        cmd: The clipboard command to use.
    Returns:
        True if processing should continue to the next file, False to quit.
    (A guided tour through your file; press SPACE to move on or Q to bail.)
    """
    try:
        stats = os.stat(filename)
        mod_date = time.ctime(stats.st_mtime)
        size = stats.st_size
        print(f"{filename} (modified: {mod_date}, size: {size} bytes)")
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
        if not copy_to_system_clipboard(text, cmd):
            print(f"Error: Clipboard copy failed for {filename}.", file=sys.stderr)
            return False
        print("Copied. Press SPACE for next file or Q to quit.", end='', flush=True)
        ch = getch()
        print()  # newline after key press
        if ch.lower() == 'q':
            return False
        return True
    except Exception as e:
        print(f"Error processing file '{filename}': {e}", file=sys.stderr)
        return False

def main() -> NoReturn:
    """
    Main function to copy text to the system clipboard.

    Operates in one of two modes:
      1. STDIN Mode: If no filenames are provided, reads from standard input.
      2. File Mode: If one or more filenames are provided, processes them as follows:
         - If exactly one file is provided (and --interactive is not specified), its contents are
           copied to the clipboard immediately.
         - If multiple files are provided, --interactive must be specified. In interactive mode,
           each file is processed one-by-one with user confirmation to proceed.
    """
    parser = argparse.ArgumentParser(
        description="Copy text to the system clipboard from STDIN or file(s)."
    )
    parser.add_argument(
        "--utility",
        choices=["xclip", "xsel", "wl-copy"],
        help="Explicitly select the clipboard utility to use."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode for processing multiple files."
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help="File(s) to read from. If provided, text is read from the file(s) instead of STDIN."
    )
    args = parser.parse_args()

    cmd = get_clipboard_command(args.utility)
    if cmd is None:
        instructions = get_installation_instructions()
        print(f"Error: No suitable clipboard utility found. {instructions}", file=sys.stderr)
        sys.exit(1)

    if args.filenames:
        if len(args.filenames) == 1 and not args.interactive:
            # Single file, non-interactive mode.
            filename = args.filenames[0]
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"Error: Unable to read file '{filename}': {e}", file=sys.stderr)
                sys.exit(1)
            if not copy_to_system_clipboard(text, cmd):
                instructions = get_installation_instructions()
                print(f"Error: Clipboard copy failed. {instructions}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)
        else:
            # Multiple files provided; interactive mode is required.
            if not args.interactive:
                print("Error: Multiple files provided. Use --interactive mode to process multiple files.", file=sys.stderr)
                sys.exit(1)
            for filename in args.filenames:
                if not process_file(filename, cmd):
                    break
            sys.exit(0)
    else:
        # No filenames provided; read from STDIN.
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        text = sys.stdin.read()
        if not text:
            print("Error: No text to copy.", file=sys.stderr)
            sys.exit(1)
        if not copy_to_system_clipboard(text, cmd):
            instructions = get_installation_instructions()
            print(f"Error: Clipboard copy failed. {instructions}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    main()


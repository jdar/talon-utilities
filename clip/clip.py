#!/usr/bin/env python3
# talon-utilities/clip/clip.py
"""
clip.py - Copy text from standard input to the system clipboard using an external utility,
with an option to override the underlying utility.

Authors:
    Matt Heck, President, Hard Problems Group, LLC
    R. Talon

License: Refer to the LICENSE file.

This utility reads from stdin and attempts to copy text to the system clipboard using a
detected external clipboard utility (xclip, xsel, or wl-copy). You can explicitly override
the utility using the command-line option --utility; otherwise, the script selects the most
appropriate utility based on your environment. If no appropriate utility is found or the copy
operation fails, the script exits with an error message suggesting the necessary installation.
(No temporary file fallback here—if your environment isn't set up, we simply throw a fit.)
"""

import os
import sys
import subprocess
import shutil
import argparse
from typing import Optional, List, NoReturn, Tuple

def get_clipboard_command(preferred: Optional[str] = None) -> Optional[List[str]]:
    """
    Determine the available clipboard command.

    If a preferred utility is provided, verify its presence; otherwise, choose the most
    appropriate utility based on the environment (Wayland or X11).

    Args:
        preferred: The preferred clipboard utility to use (xclip, xsel, or wl-copy), if any.
    Returns:
        A list representing the command and its arguments if available, else None.
    (Explicit or implicit choice—pick your poison, but if none is available, we bail.)
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

    # No preferred utility specified; select based on environment.
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
    (No graceful fallback here—if the clipboard utility fails, we throw an error.)
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
    Provide instructions for installing a suitable clipboard utility based on the current environment.

    Returns:
        A string with installation instructions.
    (Telling you exactly what to do when your system is missing a crucial component.)
    """
    if os.environ.get("WAYLAND_DISPLAY"):
        return ("Please install 'wl-copy' (e.g., sudo dnf install wl-clipboard or "
                "sudo apt install wl-clipboard) for Wayland.")
    elif os.environ.get("DISPLAY"):
        return ("Please install 'xclip' (e.g., sudo dnf install xclip or "
                "sudo apt install xclip) or 'xsel' for X11.")
    else:
        return "No graphical environment detected. Clipboard functionality requires a GUI environment with a clipboard utility installed."

def parse_args() -> Tuple[argparse.Namespace, argparse.ArgumentParser]:
    """
    Parse command-line arguments.

    Returns:
        A tuple of the argparse.Namespace with parsed options and the parser itself.
    (Because sometimes you want to override the system's decisions—and sometimes display usage.)
    """
    parser = argparse.ArgumentParser(
        description="Copy text from standard input to the system clipboard using an external utility."
    )
    parser.add_argument(
        "--utility",
        choices=["xclip", "xsel", "wl-copy"],
        help="Explicitly select the clipboard utility to use."
    )
    args = parser.parse_args()
    return args, parser

def main() -> NoReturn:
    """
    Main function to copy text from standard input to the clipboard.

    Reads from standard input and attempts to copy to the system clipboard using an external utility.
    If unsuccessful, throws an error with installation instructions.
    (If you haven't piped text into the script, you'll see usage information.)
    """
    args, parser = parse_args()

    # If no input is piped, display usage information and exit.
    if sys.stdin.isatty():
        parser.print_help()
        sys.exit(1)

    text = sys.stdin.read()
    if not text:
        print("Error: No text to copy.", file=sys.stderr)
        sys.exit(1)

    cmd = get_clipboard_command(args.utility)
    if cmd is None:
        instructions = get_installation_instructions()
        print(f"Error: No suitable clipboard utility found. {instructions}", file=sys.stderr)
        sys.exit(1)

    if not copy_to_system_clipboard(text, cmd):
        instructions = get_installation_instructions()
        print(f"Error: Clipboard copy failed. {instructions}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()

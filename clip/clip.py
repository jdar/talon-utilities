#!/usr/bin/env python3
# talon-utilities/clip/clip.py
"""
clip.py - Copy text to the system clipboard from STDIN or file(s).

Authors:
    Matt Heck, President, Hard Problems Group, LLC
    R. Talon

License: Refer to the LICENSE file.

This utility operates in multiple modes:
1. STDIN Mode (default): If no filename is provided, text is read from standard input.
2. File Mode:
   - If exactly one file is provided (and neither --interactive nor --stream is specified),
     the file’s content is copied to the clipboard immediately.
   - If multiple files (or a filespec matching multiple files) are provided, you must specify
     either the --interactive option or the new --stream option.
     * --interactive: Processes files one-by-one. For each file, the filename, modification date,
       and size are displayed; the file’s content is copied to the clipboard; then the user is
       prompted "Copied. Press SPACE for next file or Q to quit."
     * --stream: Concatenates all files into a single buffer by wrapping each file’s content with
       markers. A batch header (including username, hostname, working directory, and timestamp)
       is prepended, and each file is wrapped in a header and footer indicating its name, modification
       timestamp, and byte size. Finally, a batch footer is appended.
(No temporary fallback is provided; errors in clipboard copy are fatal.)
"""

import os
import sys
import subprocess
import shutil
import argparse
import random
import time
import termios
import tty
import getpass
import socket
from typing import Optional, List, NoReturn

def get_clipboard_command(preferred: Optional[str] = None) -> Optional[List[str]]:
    """
    Determine the available clipboard command.

    If a preferred utility is provided, verify its presence; otherwise, choose the most
    appropriate utility based on the environment.
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

def process_files_stream(filenames: List[str], cmd: List[str]) -> bool:
    """
    Process multiple files in stream mode by concatenating them into a single buffer
    with wrapping markers.
    """
    # Gather batch header information
    username = getpass.getuser()
    hostname = socket.gethostname()
    cwd = os.getcwd()
    current_ts = time.strftime("%d%b%Y%p%H%M%S", time.localtime())
    batch_header = (f"========BEGIN BATCH TRANSFER FROM {username}@{hostname}:{cwd} AT {current_ts}========\n")
    buffer_list = [batch_header]
    total_files = 0
    total_bytes = 0

    for filename in filenames:
        try:
            stats = os.stat(filename)
            mod_ts = time.strftime("%d%b%Y%p%H%M%S", time.localtime(stats.st_mtime))
            size = stats.st_size
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error processing file '{filename}': {e}", file=sys.stderr)
            return False

        total_files += 1
        total_bytes += size
        file_basename = os.path.basename(filename).upper()
        file_header = f"===========BEGIN {file_basename}, MODIFIED {mod_ts}===========\n"
        file_footer = f"===========END {file_basename}, TOTAL {size} BYTES===========\n"
        buffer_list.append(file_header)
        buffer_list.append(content + "\n")
        buffer_list.append(file_footer)

    batch_footer = f"========END BATCH TRANSFER, TOTAL {total_files} FILES, {total_bytes} bytes========\n"
    witty_quips = [
        "(Transfer complete: the world is now your clipboard.)",
        "THANK YOU FOR USING TALON UTILITIES - NO CHARGE TO CALLING PARTY",
        "Clipboard assembled: mission accomplished!",
        "Operation 'Copy-Paste' successful. Onward!",
        "Your data has been delivered. Now go forth and paste.",
        "A flawless execution—clipboard now holds your treasures.",
        "Clipboard operation complete. You might want to brag about this.",
        "Files consolidated, clipboard activated. Let the pasting begin.",
        "Data fusion achieved—your clipboard is the new command center.",
        "Batch mode: engaged. Your files are now one with the clipboard.",
        "Data delivered—now go forth and paste like a champion.",
        "Clipboard updated. It’s not a revolution, just another day.",
        "Data transferred. Trust me, it’s barely impressive.",
        "Operation complete. Your clipboard now bears the burden of mediocrity.",
        "Files merged. The clipboard’s content is as cynical as its owner.",
        "Clipboard loaded. A small victory in an indifferent cosmos.",
        "Data delivered. Enjoy your clipboard, if you can muster enthusiasm.",
        "Mission accomplished. Your clipboard now holds what little hope remains.",
        "Copy operation successful. Don’t let it inflate your ego.",
        "Transfer complete. At least your clipboard works in an otherwise failing system.",
        "Files consolidated. In a universe of chaos, your clipboard stands as the lone obedient servant."    ]
    ending_line = "============================================================\n"

    buffer_list.append(batch_footer)
    witty_quip = random.choice(witty_quips)+"\n"
    buffer_list.append(witty_quip)
    buffer_list.append(ending_line)
    final_buffer = "".join(buffer_list)

    if not copy_to_system_clipboard(final_buffer, cmd):
        print("Error: Clipboard copy failed in stream mode.", file=sys.stderr)
        return False
    return True

def main() -> NoReturn:
    """
    Main function to copy text to the system clipboard.

    Operates in one of two modes:
      1. STDIN Mode: If no filenames are provided, reads from standard input.
      2. File Mode: If one or more filenames are provided, processes them as follows:
         - If exactly one file is provided (and --interactive is not specified), its contents are
           copied to the clipboard immediately.
         - If multiple files are provided, either --interactive or --stream must be specified.
           In interactive mode, each file is processed one-by-one with user confirmation to proceed.
           In stream mode, files are wrapped in separators, as is the overall batch.
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
        "--stream",
        action="store_true",
        help="Enable stream mode for processing multiple files by concatenating them into a single buffer with wrapping markers."
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
        # Single file mode: if exactly one file and neither interactive nor stream mode specified.
        if len(args.filenames) == 1 and not (args.interactive or args.stream):
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
            # Multiple files provided; either --interactive or --stream must be specified.
            if not (args.interactive or args.stream):
                print("Error: Multiple files provided. Use --interactive or --stream mode to process multiple files.", file=sys.stderr)
                sys.exit(1)
            if args.interactive:
                for filename in args.filenames:
                    if not process_file(filename, cmd):
                        break
                sys.exit(0)
            elif args.stream:
                if not process_files_stream(args.filenames, cmd):
                    sys.exit(1)
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


#!/usr/bin/env python3
# talon-utilities/pip-update/install.py
"""
Installs the pip-update script either system-wide (if root)
or in a suitable local bin directory otherwise (because
the shell apparently didn't want to cooperate).

Author(s):
Matt Heck, President, Hard Problems Group, LLC.
R. Talon

License Reference: See LICENSE.txt in parent directory (the usual disclaimers apply).
"""

import os
import sys
import shutil
import stat
from typing import List

def expand_path(path: str) -> str:
    """
    Expands a tilde or environment variables in the given path.
    (Even though I suspect you know how to handle your own home directory.)
    """
    return os.path.expanduser(os.path.expandvars(path))

def in_path(dir_path: str) -> bool:
    """
    Checks if dir_path is present in the user's PATH environment variable.
    (One might say you should manage your own PATH, but let's do it anyway.)
    """
    for p in os.environ.get("PATH", "").split(os.pathsep):
        # Compare normalized absolute paths
        if os.path.abspath(p) == os.path.abspath(dir_path):
            return True
    return False

def find_local_bin_directory() -> str:
    """
    Attempts to find a suitable local bin directory in the user's PATH first,
    then checks if any known directories exist, and finally falls back to ~/.local/bin.
    (A valiant attempt at mind-reading.)
    """
    local_candidates = ["~/bin", "~/.bin", "~/.local/bin", "~/.local/.bin"]

    # 1. Check if any candidate is already in PATH:
    for candidate in local_candidates:
        expanded = expand_path(candidate)
        if in_path(expanded):
            return expanded

    # 2. If none were in PATH, check if any exist on disk:
    for candidate in local_candidates:
        expanded = expand_path(candidate)
        if os.path.isdir(expanded):
            return expanded

    # 3. If not found, fallback to ~/.local/bin:
    return expand_path("~/.local/bin")

def install_pip_update() -> None:
    """
    Installs pip-update either system-wide (if we're root) or user-local.
    Copies pip-update.py to 'pip-update' (with a Python shebang) and marks it executable.
    (Better than letting the shell guess wrong about how to run it.)
    """
    # If root, install system-wide:
    if os.geteuid() == 0:
        system_dir = "/usr/local/bin"
        print(f"Detected root privileges. Installing system-wide to: {system_dir}")
        os.makedirs(system_dir, exist_ok=True)
        install_to_path("pip-update.py", os.path.join(system_dir, "pip-update"))
    else:
        local_bin = find_local_bin_directory()
        print(f"Installing pip-update to a user-local bin directory: {local_bin}")
        os.makedirs(local_bin, exist_ok=True)
        install_to_path("pip-update.py", os.path.join(local_bin, "pip-update"))

def install_to_path(source_file: str, destination_file: str) -> None:
    """
    Copies source_file to destination_file, ensures the correct Python shebang,
    and marks it executable. (Because the system has no idea what it's copying otherwise.)
    """
    # Read pip-update.py, ensure we have or add a #!/usr/bin/env python3 if absent:
    with open(source_file, "r", encoding="utf-8") as f:
        contents = f.read()

    # If we want to forcibly ensure a shebang at the top, let's do so:
    shebang = "#!/usr/bin/env python3"
    if not contents.startswith(shebang):
        # Insert the shebang + a newline at the top
        contents = f"{shebang}\n{contents}"

    # Write out to the destination:
    with open(destination_file, "w", encoding="utf-8") as f:
        f.write(contents)

    # Make executable
    st = os.stat(destination_file)
    os.chmod(destination_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installation complete. Binary is at: {destination_file}")

    # If it's not in PATH, gently nag the user:
    parent = os.path.dirname(destination_file)
    if not in_path(parent):
        print(f"Warning: {parent} is not in your PATH.")
        print("Add it to your PATH or call 'pip-update' explicitly.")

def main() -> None:
    """
    Main entry point for install.py.
    (Because sometimes a Python script is just simpler than a shell script.)
    """
    print("Installing pip-update script via Python installer...")
    install_pip_update()
    print("(Try running 'pip-update --help' now, or open a new shell if needed.)")

if __name__ == "__main__":
    main()


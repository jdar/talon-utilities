pip-update Utility
==================

Overview:
---------
This utility provides bulk-update functionality for Python pip packages.
It performs the following steps:
 1. Runs "pip check" before upgrading.
 2. Lists outdated packages and upgrades them individually.
 3. Runs "pip check" again to detect any new conflicts.
 4. Prints a color-coded summary table of each upgrade's result ("OK", "WARNINGS", "WEIRD", or "FAILED").

Also supports:
  - --skip <pkgname> to skip certain packages.
  - --dry-run to only show which packages would be updated.
  - --force to ignore pre-upgrade conflicts.
  - --report <file.json> to capture environment metadata, upgrade results, etc.
  - --nocolor / --forcecolor to control terminal color usage explicitly.

Installation:
-------------
 1. Make sure you have Python 3.11+ installed.
 2. Run install.py as root (for a system-wide install) or as a normal user (for a user-local install).
 3. Ensure the resulting path is in your $PATH.

Uninstallation:
---------------
 1. Run uninstall.py as root (for a system-wide removal) or a normal user (for user-local).
 2. Man pages are also removed if found.

Tips & Notes:
-------------
 - If you see "pip check" conflicts, it means some package versions are out of sync with others.
 - "WEIRD" indicates that a freshly updated package is implicated in new post-upgrade conflicts.
 - A typical usage might be "pip-update --skip torch" if Torch or other libraries have pinned GPU dependencies.

Author(s):
----------
- Matt Heck, President, Hard Problems Group, LLC.
- R. Talon

License:
--------
See LICENSE.txt in the project root.


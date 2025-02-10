#!/usr/bin/env python3
# talon-utilities/pip-update/pip-update.py
"""
Automates updating of all local pip packages (because apparently "pip update" is too much to ask).
Now with pre/post 'pip check', forced installs, color-coded summaries, JSON reporting,
and environment metadata (username, hostname, timestamp, Python/pip versions, venv detection).

Author(s): Hard Problems Group, LLC.  R. Talon
License Reference: See LICENSE.txt in parent directory (the usual disclaimers apply).

Usage:
    python3 pip-update.py [--skip PKG1 PKG2 ...]
                          [--dry-run]
                          [--force]
                          [--nocolor]
                          [--forcecolor]
                          [--report OUTFILE.json]

Example:
    python3 pip-update.py --skip pip --skip setuptools
    python3 pip-update.py --dry-run
    python3 pip-update.py --force --report results.json

Behavioral Notes:
1. We run a 'pip check' before upgrading. If conflicts exist, we abort (unless --force is used).
2. We upgrade packages one by one.
3. We run 'pip check' again, marking new conflicts as "WEIRD" or "WARNINGS."
4. We produce a color-coded summary table if running interactively.
5. We optionally write a JSON report (including environment metadata).

Dependencies:
    - Python 3.11 or higher
    - pip

Environment:
    - Ubuntu 22+, Fedora 41, RHEL 9.5, or basically any Linux with Python/pip.
"""

import sys
import os
import subprocess
import json
import argparse
import getpass
import socket
import platform
from datetime import datetime
from typing import List, Dict, Any, Optional

def detect_pip_executable() -> str:
    """
    Determines which pip executable to call (pip, pip3, or "python -m pip").
    (Yes, we're still dancing around pip's naming chaos.)

    Returns:
        A string specifying the pip command.
    Raises:
        RuntimeError: If no pip-like command is found in PATH.
    """
    candidates = ["pip", "pip3"]
    for c in candidates:
        try:
            subprocess.run([c, "--version"], check=True, capture_output=True, text=True)
            return c
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    # Fallback: try python -m pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True,
                       capture_output=True, text=True)
        return f"{sys.executable} -m pip"
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("No working pip command found in PATH.")

def get_pip_version(pip_cmd: str) -> str:
    """
    Attempts to retrieve the pip version string by calling `pip --version`.
    (We'll just store the entire returned line.)
    """
    try:
        result = subprocess.run((pip_cmd.split() + ["--version"]),
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "Unknown pip version"

def pip_check_issues(pip_cmd: str) -> List[str]:
    """
    Runs 'pip check' and captures any environment conflict warnings.
    (Because pip’s “resolver” occasionally needs a chaperone.)

    Args:
        pip_cmd: The pip command or python -m pip invocation.
    Returns:
        A list of lines describing each reported conflict (if any).
    """
    cmd = f"{pip_cmd} check"
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, check=False)
        output_lines = result.stdout.strip().splitlines()
        error_lines = result.stderr.strip().splitlines()
        # If 'pip check' reports issues, usually returncode=1 and it prints to stdout.
        if result.returncode != 0:
            return output_lines + error_lines
        return output_lines + error_lines
    except Exception as e:
        return [f"Error running pip check: {e}"]

def get_outdated_packages(pip_cmd: str) -> List[Dict[str, Any]]:
    """
    Retrieves a list of outdated packages via pip's JSON output or a fallback textual parse.
    (Yes, let's parse JSON if we can, but older pip may not support it.)

    Args:
        pip_cmd: The pip command or "python -m pip" invocation string.
    Returns:
        A list of dicts with keys: name, current_version, latest_version, etc.
    Raises:
        RuntimeError: If pip list fails or returns no data.
    """
    cmd = f"{pip_cmd} list --outdated --format=json"
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if not isinstance(data, list):
            raise ValueError("Expected a list in JSON output.")
        return data
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        # Fallback: parse the textual output from "pip list --outdated"
        fallback_cmd = f"{pip_cmd} list --outdated"
        try:
            fallback_result = subprocess.run(fallback_cmd.split(), capture_output=True,
                                             text=True, check=True)
            lines = fallback_result.stdout.splitlines()
            outdated = []
            for line in lines:
                if "Package" in line and "Version" in line and "Latest" in line:
                    continue  # skip header
                parts = line.split()
                if len(parts) >= 3:
                    outdated.append({
                        "name": parts[0],
                        "version": parts[1],         # current
                        "latest_version": parts[2]   # new
                    })
            return outdated
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to retrieve outdated packages: {e}")

def upgrade_package(pip_cmd: str, pkg_name: str, dry_run: bool = False) -> bool:
    """
    Upgrades an individual package using pip.
    (So if something fails, you can blame it on that package alone.)

    Args:
        pip_cmd: The pip invocation string.
        pkg_name: The name of the package to upgrade.
        dry_run: If True, do not actually perform the upgrade, just show it.
    Returns:
        True if upgrade successful (or simulated success in dry-run).
    Raises:
        RuntimeError: If the pip install --upgrade command fails.
    """
    if dry_run:
        print(f"[DRY RUN] Would upgrade: {pkg_name}")
        return True
    cmd = f"{pip_cmd} install --upgrade {pkg_name}"
    print(f"Upgrading {pkg_name} ...")
    try:
        subprocess.run(cmd.split(), check=True)
        return True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to upgrade {pkg_name}: {e}")

#
# Terminal color support
#
ANSI_RESET = "\033[0m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_ORANGE = "\033[38;5;214m"  # 256-color approximation

def supports_color() -> bool:
    """
    Checks if we should use color by verifying that stdout is a TTY
    and the environment variable TERM isn't "dumb."
    """
    if not sys.stdout.isatty():
        return False
    term = (os.environ.get("TERM") or "dumb").lower()
    if term in ["dumb", ""]:
        return False
    return True

def color_text(text: str, color_code: str) -> str:
    """Wrap text in ANSI color codes if color is enabled."""
    return f"{color_code}{text}{ANSI_RESET}"

def collect_env_metadata(pip_cmd: str) -> Dict[str, Any]:
    """
    Collects environment metadata like user, host, timestamp, python/pip version,
    and whether we're in a virtual environment. (Because knowledge is half the battle.)
    """
    username = getpass.getuser() or os.environ.get("USER", "unknown_user")
    hostname = socket.gethostname()
    timestamp = datetime.now().isoformat()
    python_ver = platform.python_version()
    pip_ver = get_pip_version(pip_cmd)

    # Check for typical environment indicators
    # We'll guess if sys.base_prefix != sys.prefix or 'VIRTUAL_ENV' in os.environ -> some venv is active
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    in_venv = (base_prefix != sys.prefix) or ("VIRTUAL_ENV" in os.environ) or ("CONDA_DEFAULT_ENV" in os.environ)

    return {
        "username": username,
        "hostname": hostname,
        "timestamp": timestamp,
        "python_version": python_ver,
        "pip_version": pip_ver,
        "virtual_environment_active": in_venv
    }

def main() -> None:
    """
    Main entry point for pip-update script, now with forced dependency checks,
    color-coded final statuses, optional JSON reporting, and environment metadata.
    """
    parser = argparse.ArgumentParser(description="Update all pip packages in the current environment, with extra safety checks.")
    parser.add_argument("--skip", nargs="+", default=[],
                        help="Specify package(s) to skip upgrading.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Perform a dry run; show what would be updated without doing it.")
    parser.add_argument("--force", action="store_true",
                        help="Ignore pre-upgrade 'pip check' issues and proceed anyway (not recommended).")
    parser.add_argument("--nocolor", action="store_true",
                        help="Disable color output entirely.")
    parser.add_argument("--forcecolor", action="store_true",
                        help="Force color output even if terminal detection says otherwise.")
    parser.add_argument("--report", metavar="OUTFILE", type=str,
                        help="Write a JSON report of the upgrade process (including environment metadata) to the specified file.")
    args = parser.parse_args()

    # Decide color usage:
    if args.forcecolor:
        use_color = True
    elif args.nocolor:
        use_color = False
    else:
        use_color = supports_color()

    def c(text: str, ansi_code: str) -> str:
        """Convenient shortcut for color_text if color is enabled."""
        if use_color:
            return color_text(text, ansi_code)
        return text

    # Attempt to detect pip:
    try:
        pip_cmd = detect_pip_executable()
    except RuntimeError as e:
        print(f"Error detecting pip: {e}", file=sys.stderr)
        sys.exit(1)

    # Gather environment metadata early (so we can store it in the JSON if needed)
    env_info = collect_env_metadata(pip_cmd)

    # Pre-upgrade pip check:
    pre_check_issues = pip_check_issues(pip_cmd)
    if pre_check_issues:
        print(c("Pre-Upgrade Issues Detected (via pip check):", ANSI_RED))
        for line in pre_check_issues:
            print("  " + line)
        if not args.force:
            print(c("\nAborting due to environment conflicts. Use --force to override.", ANSI_RED))
            # If the user wants a report anyway, we can produce it (with no upgrade results).
            if args.report:
                generate_report(args.report, env_info, pre_check_issues, [], [], [], forced=False)
            sys.exit(1)
        else:
            print(c("\n--force specified; ignoring these issues and forging ahead. Good luck.", ANSI_YELLOW))

    # Retrieve the list of outdated packages:
    try:
        outdated = get_outdated_packages(pip_cmd)
    except RuntimeError as e:
        print(f"Error listing outdated packages: {e}", file=sys.stderr)
        sys.exit(1)

    if not outdated:
        print("No outdated packages found. (All is well... supposedly.)")
        if args.report:
            generate_report(args.report, env_info, pre_check_issues, [], [], [], forced=args.force)
        sys.exit(0)

    # We'll store data about what we upgraded
    upgrade_results = []

    # Standardize fields for old/new version tracking
    for item in outdated:
        pkg_name = item.get("name", "")
        current_ver = item.get("version") or item.get("current_version") or "?"
        latest_ver = item.get("latest_version") or "?"
        if not pkg_name or pkg_name in args.skip:
            continue

        result_entry = {
            "name": pkg_name,
            "old_version": current_ver,
            "new_version": latest_ver,
            "status": "OK",
            "error_msg": ""
        }

        if args.dry_run:
            print(f"[DRY RUN] Would upgrade {pkg_name} from {current_ver} to {latest_ver}")
            continue

        # Attempt the upgrade
        try:
            upgrade_package(pip_cmd, pkg_name)
        except RuntimeError as e:
            result_entry["status"] = "FAILED"
            result_entry["error_msg"] = str(e)

        upgrade_results.append(result_entry)

    # Post-upgrade pip check:
    post_check_issues = pip_check_issues(pip_cmd)

    # Mark newly weird or warnings
    if post_check_issues:
        # If a line specifically mentions a package we upgraded, mark it as "WEIRD"
        for line in post_check_issues:
            for r in upgrade_results:
                if r["status"] == "OK" and r["name"].lower() in line.lower():
                    r["status"] = "WEIRD"
                    r["error_msg"] = line

        # For others that remain "OK", mark them as "WARNINGS"
        for r in upgrade_results:
            if r["status"] == "OK":
                r["status"] = "WARNINGS"
                r["error_msg"] = "Other environment issues detected."

    # Print final summary table:
    if not args.dry_run:
        print("\nFinal Upgrade Report\n====================")
        print(f"{'Package':30} {'Old':15} {'New':15} {'Status':10}")
        print("-" * 75)
        for r in upgrade_results:
            status_text = r["status"]
            if r["status"] == "OK":
                status_text = c("OK", ANSI_GREEN)
            elif r["status"] == "FAILED":
                status_text = c("FAILED", ANSI_RED)
            elif r["status"] == "WARNINGS":
                status_text = c("WARNINGS", ANSI_YELLOW)
            elif r["status"] == "WEIRD":
                status_text = c("WEIRD", ANSI_ORANGE)

            print(f"{r['name'][:29]:30} {r['old_version'][:14]:15} {r['new_version'][:14]:15} {status_text:10}")

    # Show post-upgrade issues
    if post_check_issues:
        print("\nPost-Upgrade Issues Detected (via pip check):")
        for line in post_check_issues:
            print("  " + line)
    else:
        print("\nNo post-upgrade environment issues reported by pip check. (Miracles happen!)")

    # If user forced ignoring conflicts, let's scold them:
    if args.force:
        print(c("\nYou used --force. Pre-upgrade environment issues may still exist or have worsened.", ANSI_YELLOW))
        print("Proceed with caution, and consider reviewing environment or pinned dependencies.\n")

    # Generate a JSON report if requested:
    if args.report:
        generate_report(args.report, env_info, pre_check_issues, post_check_issues, outdated, upgrade_results, forced=args.force)
        print(f"JSON report written to {args.report}")

def generate_report(
    outfile: str,
    env_info: Dict[str, Any],
    pre_issues: List[str],
    post_issues: List[str],
    outdated_packages: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    forced: bool
) -> None:
    """
    Generates a JSON report capturing environment metadata, pre/post pip-check issues,
    the list of outdated packages, final statuses, and whether we forcibly ignored conflicts.

    Args:
        outfile: Path to the JSON file to create/overwrite.
        env_info: Dictionary of environment details (user, host, python/pip version, etc.).
        pre_issues: Lines from 'pip check' before upgrades.
        post_issues: Lines from 'pip check' after upgrades.
        outdated_packages: The raw packages we considered for updating.
        results: The final statuses for each package upgraded.
        forced: Whether --force was used (ignoring pre-upgrade conflicts).
    """
    report_data = {
        "metadata": env_info,
        "pre_check_issues": pre_issues,
        "post_check_issues": post_issues,
        "outdated_packages": outdated_packages,
        "upgrade_results": results,
        "forced_ignore_pre_upgrade_conflicts": forced
    }
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
    except Exception as e:
        print(f"Error writing JSON report {outfile}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()


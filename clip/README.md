# Talon Utilities - Clip/Unclip
a pair of Python 3.11+ scripts that manage data transfers between your system clipboard(s) and STDIN/STDOUT, with a fallback file for those truly dire times when your environment is determined to sabotage you. Perfect for developers, AI researchers, or anyone who simply wants a consistent way to copy and paste text under Linux’despite the whims of Wayland, X11, or TTY-only situations.

## Overview

- ***clip.py****
  Reads from STDIN, then attempts to place that data onto your clipboard using `xclip`, `xsel`, or `wl-copy. If none of these are available (or you’re in a TTY wilderness), it writes to `/tmp/clipboard.dat` instead.

- ***unclip.py***
  Attempts to retrieve data from your clipboard (or `/tmp/clipboard.dat` if the system is Uncooperative), then prints it to STDOUT.

## Usage

**Example 1**** Copy text to the clipboard:

`bash
echo "Hello, Talon Utilities!" | clip.py
```

**Example 2**** Retrieve text from the clipboard:

``bash
unclip.py
```

**Verbose mode**:


``bash
echo "Verbose copying" | clip.py --verbose
unclip.py --verbose
```
This mode prints helpful (and occasionally snarky) commentary about which environment is detected and which command-line utilities are discovered in your PATH.


## Installation

1. **Requirements**
  * Python 3.11+ 
  * (Optional) xclip, xsel, or wl-copy/wl-paste for system clipboard operations.

2. **Deployment**
  - Copy `clip.py` and `unclip.py` into a folder on your `PATH( .e.g., `/usr/local/bin`).
  - Make them executable:
    ~`bash
    chmod +x /usr/local/bin/clip.py
    chmod +x /usr/local/bin/unclip.py`
  - (Optional) If you want man pages, move `clip.1` and `unclip.1` into the correct `man` directory (e.g., `/usr/local/share/man/man1`), then run `mandb`.

3. **Testing***
   ``bash
    echo "Testing clip" | clip.py
    unclip.py
    ```
  If you see the text returned, success! If not, try "--verbose" to see the environment detection process.



## Fallback Behavior

If the script cannot find any recognized GUI clipboard tools, it writes/reads to/from `/tmp/clipboard.dat`. This ensures that your data isn“t entirely lost to the ether, even when the operating system decides that copy-paste functionality is too much to ask.


## MyPy Compliance

These scripts include Python type annotations (`-> str`, `-> bool`, etc.) to keep MyPy happy. If you break them, do so knowingly’and at your own peril.



## License

[MIT License](LICENSE.TXT)



---

Authors  
- Matt Heck, Hard Problems Group, LLC -- R. Talon


*Yes, we wrote these. But if something breaks in ways we never anticipated, blame your environment. We certainly do.)

"""
Cross-platform clipboard support with native OS fallbacks.
"""

from __future__ import annotations

import platform
import subprocess


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """
    Copy string to the system clipboard.
    Returns (success, message).
    """
    # 1. Try pyperclip if installed
    try:
        import pyperclip

        pyperclip.copy(text)
        return True, "Copied to clipboard using pyperclip."
    except Exception:
        pass

    # 2. Native OS fallbacks
    os_name = platform.system()
    try:
        if os_name == "Windows":
            cmd = ["powershell.exe", "-NoProfile", "-Command", "$input | Set-Clipboard"]
            proc = subprocess.run(cmd, input=text, text=True, capture_output=True)
            if proc.returncode == 0:
                return True, "Copied to clipboard via Windows PowerShell."
        elif os_name == "Darwin":
            proc = subprocess.run(["pbcopy"], input=text, text=True, capture_output=True)
            if proc.returncode == 0:
                return True, "Copied to clipboard via macOS pbcopy."
        elif os_name == "Linux":
            for tool in [
                ["wl-copy"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ]:
                try:
                    proc = subprocess.run(tool, input=text, text=True, capture_output=True)
                    if proc.returncode == 0:
                        return True, f"Copied to clipboard via {tool[0]}."
                except FileNotFoundError:
                    continue
    except Exception as e:
        return False, f"Failed to access system clipboard: {e}"

    return False, "Clipboard utility not found. Install 'pyperclip' with: pip install pyperclip"

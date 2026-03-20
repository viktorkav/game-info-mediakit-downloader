#!/usr/bin/env python3
"""Cross-platform build script for Game Info - Mediakit Downloader.

Usage:
    python build.py

Builds the application using PyInstaller for the current platform.

Note: On Windows, run this from a local drive (e.g. C:\\). PyInstaller does not
work reliably on network paths such as \\\\wsl.localhost.
"""

import os
import shutil
import subprocess
import sys


def main():
    # Clean previous builds
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)
    for f in os.listdir("."):
        if f.endswith(".spec"):
            os.remove(f)

    # Platform-specific settings
    separator = ";" if sys.platform == "win32" else ":"
    add_data = f"assets{separator}assets"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "Game Info",
        "--windowed",
        "--add-data", add_data,
        "--collect-all", "customtkinter",
        "GameInfo.py",
    ]

    print(f"Building for {sys.platform}...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    if sys.platform == "darwin":
        print("Build complete. App is in dist/Game Info.app")
    elif sys.platform == "win32":
        print("Build complete. App is in dist/Game Info/")
    else:
        print("Build complete. App is in dist/Game Info/")


if __name__ == "__main__":
    main()

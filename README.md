# Game Info Mediakit Downloader

Game Info is a cross-platform desktop app built with Python and CustomTkinter for searching the IGDB catalog and downloading high-resolution game media kits.

Tested on macOS, Windows 11, and Ubuntu 24.04.

## Features

- Search games from IGDB with a desktop UI optimized for browsing.
- Open a detailed view with release info, companies, genres, screenshots, and trailers.
- Save favorite games locally for quick access.
- Download cover art, artworks, and screenshots as a zipped media kit.
- Reuse a local platform icon database for richer search results.

## Requirements

- Python 3.9+
- An IGDB API client ID and client secret
- Linux: `tkinter` system package (e.g. `sudo apt install python3-tk` on Debian/Ubuntu)

## Local configuration

This repository does not include API credentials.

Use one of these options:

1. Set `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` in your shell environment.
2. Copy `local_config.example.json` to `local_config.json` and fill in your own values.

`local_config.json` is ignored by git and will not be published.

## Run locally

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 GameInfo.py
```

### Windows

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python GameInfo.py
```

## Build a distributable app

The cross-platform build script uses PyInstaller to package the application for the current platform:

```bash
python build.py
```

The output is placed in `dist/Game Info/` (or `dist/Game Info.app` on macOS).

### Legacy macOS build

The original macOS-only build script is still available:

```bash
chmod +x build_app.sh
./build_app.sh
```

The build script creates `dist/Game Info.app`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## Repository notes

- `favorites.json`, build artifacts, virtual environments, logs, and local configuration files are ignored.
- The existing `assets/` directory contains app resources and platform icons used by the UI.

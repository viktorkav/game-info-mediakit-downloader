# Game Info Mediakit Downloader

Game Info is a macOS desktop app built with Python and CustomTkinter for searching the IGDB catalog and downloading high-resolution game media kits.

## Features

- Search games from IGDB with a desktop UI optimized for browsing.
- Open a detailed view with release info, companies, genres, screenshots, and trailers.
- Save favorite games locally for quick access.
- Download cover art, artworks, and screenshots as a zipped media kit.
- Reuse a local platform icon database for richer search results.

## Requirements

- Python 3.9+
- An IGDB API client ID and client secret

## Local configuration

This repository does not include API credentials.

Use one of these options:

1. Set `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` in your shell environment.
2. Copy `local_config.example.json` to `local_config.json` and fill in your own values.

`local_config.json` is ignored by git and will not be published.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 GameInfo.py
```

## Build the macOS app

```bash
chmod +x build_app.sh
./build_app.sh
```

The build script creates `dist/Game Info.app`.

## Repository notes

- `favorites.json`, build artifacts, virtual environments, logs, and local configuration files are ignored.
- The existing `assets/` directory contains app resources and platform icons used by the UI.

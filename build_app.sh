#!/bin/bash

source venv/bin/activate
echo "Using Python: $(which python)"

echo "Installing requirements..."
pip install pyinstaller
pip install -r requirements.txt

echo "Cleaning previous builds..."
rm -rf build dist *.spec

echo "Building Game Info..."
# --collect-all customtkinter: Ensures theme files are included
# --add-data "assets:assets": Includes local icon DB and cache
# --windowed: No terminal pop-up
# --noconfirm: Don't ask to overwrite
python -m PyInstaller --noconfirm --clean \
    --name "Game Info" \
    --windowed \
    --add-data "assets:assets" \
    --collect-all customtkinter \
    GameInfo.py

echo "Build complete. App is in dist/Game Info.app"

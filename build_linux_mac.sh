#!/usr/bin/env bash
set -e

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

pyinstaller --noconfirm --onefile --windowed taskbill.py

echo "Build finished. Look in ./dist/taskbill"

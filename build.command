#!/bin/bash
cd "$(dirname "$0")"
python3 build.py || python build.py
echo
read -p "Press Enter to close..."

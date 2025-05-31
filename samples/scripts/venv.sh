#!/bin/bash

# Create virtual environment and install dependencies
python3 -m venv .venv
. .venv/bin/activate && python3 -m pip install playwright==1.41.0
. .venv/bin/activate && playwright install chromium

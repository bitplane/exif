#!/bin/bash
# Wrapper to call the Python downloader with correct arguments
# Usage: download.sh <target_file> <url>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <target_file> <url>"
    exit 1
fi

TARGET="$1"
URL="$2"

# Strip the data/ prefix if present
FILENAME="${TARGET#data/}"

# Call the Python script
exec ./scripts/dpreview/download_sample.py "$FILENAME" "$URL"
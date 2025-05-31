#!/bin/bash
# Download a file from URL
# Usage: download.sh <filename> <url>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <filename> <url>"
    exit 1
fi

FILENAME="$1"
URL="$2"
TMPFILE="${FILENAME}.tmp"

# Create directory structure if needed
mkdir -p "$(dirname "$FILENAME")"

echo "Downloading: $FILENAME" >&2

# Download to temp file
curl -s -o "$TMPFILE" "$URL"

# Atomic move
mv "$TMPFILE" "$FILENAME"
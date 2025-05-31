#!/bin/bash
# Download and extract Wikimedia dump links
# Usage: download_and_extract.sh <url> <output_file>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <url> <output_file>"
    exit 1
fi

URL="$1"
OUTPUT="$2"
TMPFILE="${OUTPUT}.tmp"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT")"

echo "Downloading and processing: $URL" >&2
echo "Output: $OUTPUT" >&2

# Download, decompress, extract links, save to temp file
curl -s "$URL" | \
    zcat | \
    "$(dirname "$0")/extract_links.php" > "$TMPFILE"

# Check if we got any output
if [ ! -s "$TMPFILE" ]; then
    echo "Error: No output generated" >&2
    rm -f "$TMPFILE"
    exit 1
fi

# Atomic move to final location
mv "$TMPFILE" "$OUTPUT"

echo "Complete: $(wc -l < "$OUTPUT") URLs extracted" >&2
#!/bin/bash
# Get URL and store it with correct mtime for make dependency tracking
# Usage: get_url.sh <output_file>

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <output_file>"
    exit 1
fi

OUTPUT="$1"
URL="https://dumps.wikimedia.org/commonswiki/latest/commonswiki-latest-image.sql.gz"

# Get headers including Last-Modified
HEADERS=$(curl -s -D - --head "$URL")

# Extract Last-Modified header
LAST_MODIFIED=$(echo "$HEADERS" | grep -i "^Last-Modified:" | sed 's/^[^:]*: *//' | tr -d '\r')

# Store the URL in the file
echo "$URL" > "$OUTPUT"

# Set mtime to match remote file (don't fail if this doesn't work)
touch -d "$LAST_MODIFIED" "$OUTPUT" 2>/dev/null || true

echo "URL file created: $OUTPUT" >&2
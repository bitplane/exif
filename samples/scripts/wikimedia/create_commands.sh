#!/bin/bash
# Create download commands from extracted links
# Usage: create_commands.sh <input_file> <output_file>

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    exit 1
fi

INPUT="$1"
OUTPUT="$2"
TMPFILE="${OUTPUT}.tmp"

echo "Sorting links from: $INPUT" >&2
echo "Output to: $OUTPUT" >&2

# Reverse, get unique by first field, sort by count
# tail -r works on both macOS and most Unix systems
tail -r "$INPUT" | \
    sort -k1,1 -u | \
    sort -k2,2 -nr | \
    awk -F'\t' '{
        # Extract fields
        filename = $1
        count = $2
        url = $3
        
        # Check prefix and decide if included
        if (index(filename, "errors/") == 1 || 
            index(filename, "device/") == 1 ||
            (index(filename, "software/") == 1 && count >= 128) ||
            (index(filename, "tags/") == 1 && count >= 128)) {
            print "./scripts/wikimedia/download.sh " filename " " url
        }
    }' > "$TMPFILE"

# Atomic move
mv "$TMPFILE" "$OUTPUT"

echo "Sorted $(wc -l < "$OUTPUT") unique links" >&2
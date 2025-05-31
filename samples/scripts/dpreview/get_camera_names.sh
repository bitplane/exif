#!/bin/bash

# Read gallery URL and title from stdin (tab-separated), output Manufacturer/Model format
read -r input
url=""
title=""

# Parse URL and title from tab-separated input
if [[ "$input" == *$'\t'* ]]; then
    url=$(echo "$input" | cut -f1)
    title=$(echo "$input" | cut -f2)
else
    # Fallback if no tab
    title="$input"
fi

# Extract manufacturer
manufacturer=$(echo -n "Extract the camera manufacturer from this gallery.
Title: $title
URL: $url

Rules:
- Output ONLY the manufacturer name, nothing else
- NO special characters, NO punctuation, NO extra text
- Use proper capitalization: Canon, Nikon, Sony, Olympus, Fujifilm, Panasonic, etc.
- For 'Fuji' use 'Fujifilm'
- For phone brands like 'OnePlus' keep as is
- Look for common camera brands even if abbreviated (e.g. 'EOS' means Canon, 'Alpha' or 'a' series means Sony)
- If URL contains manufacturer name, use it as a hint
- Only output UNKNOWN if you really can't determine the manufacturer

Output:" | ollama run llama3 2>/dev/null | grep -v "The extracted" | head -1 | xargs)

# Extract model
model=$(echo -n "Extract the camera model from this gallery.
Title: $title
URL: $url

Rules:
- Output ONLY the model name/number, nothing else
- NO special characters except underscores, NO punctuation, NO extra text
- Do NOT include the manufacturer name
- Replace spaces with underscores
- Replace special characters with underscores
- If unclear, output exactly: UNKNOWN

Examples:
- 'Canon EOS 5D' -> 'EOS_5D'
- 'Sony a6500' -> 'a6500'
- 'OnePlus 5' -> '5'
- 'Nikon Z 9' -> 'Z_9'

Output:" | ollama run llama3 2>/dev/null | grep -v "The extracted" | head -1 | xargs)

# Validate and clean up
if [[ -z "$manufacturer" || "$manufacturer" == *"extracted"* || "$manufacturer" == *":"* || "$manufacturer" == "UNKNOWN" ]]; then
    manufacturer="UNKNOWN"
fi

if [[ -z "$model" || "$model" == *"extracted"* || "$model" == *":"* || "$model" == *"->"* || "$model" == "UNKNOWN" ]]; then
    model="UNKNOWN"
fi

# Skip if both are unknown
if [[ "$manufacturer" == "UNKNOWN" && "$model" == "UNKNOWN" ]]; then
    # Don't output anything for unknown cameras
    exit 0
fi

# Combine them
camera_info="${manufacturer}/${model}"

# Replace any problematic characters
camera_info="${camera_info//\*/}"
camera_info="${camera_info// /_}"
camera_info="${camera_info//-/_}"
camera_info="${camera_info//[^a-zA-Z0-9\/_]/}"

# Output the full params line
echo "device/$camera_info.jpg $url"
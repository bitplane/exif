#!/bin/bash

# Model to use for extraction
MODEL="llama3"

# Ensure the model is downloaded
if ! ollama list | grep -q "^$MODEL"; then
    echo "Downloading $MODEL..." >&2
    ollama pull "$MODEL" >&2
fi

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

# Only process URLs that contain "review"
if [[ ! "$url" =~ review ]]; then
    echo "  Skipping - not a review URL" >&2
    exit 0
fi

echo "Processing: $title" >&2

# Check if title suggests it's a lens before calling LLM
if [[ "$title" =~ [0-9]+mm || "$title" =~ [0-9]+-[0-9]+mm || "$title" =~ [Ff][0-9]\.[0-9] || "$title" =~ [Ff][0-9]-[0-9] ]]; then
    echo "  Skipping - appears to be a lens gallery" >&2
    exit 0
fi

# Step 1: Determine device type
device_type=$(echo -n "Gallery: $title

What type of device took these photos? Reply with ONLY one word:
Camera, Phone, Tablet, Lens, Computer, Game, Unknown

Answer:" | ollama run "$MODEL" 2>/dev/null | grep -v '^$' | tail -1 | xargs)

echo "  Device type: $device_type" >&2

# Only keep Camera, Phone, Tablet
if [[ "$device_type" != "Camera" && "$device_type" != "Phone" && "$device_type" != "Tablet" ]]; then
    echo "  Skipping - not a camera/phone/tablet" >&2
    exit 0
fi

# Step 2: Extract manufacturer
manufacturer=$(echo -n "Gallery of photos from a $device_type: $title

What manufacturer made this $device_type? Reply with ONLY the brand name.
Examples: Canon, Nikon, Sony, Fujifilm, Google, Apple, Samsung

Answer:" | ollama run "$MODEL" 2>/dev/null | grep -v '^$' | tail -1 | xargs)

echo "  Manufacturer: $manufacturer" >&2

# Check if manufacturer is valid
if [[ -z "$manufacturer" || "$manufacturer" == "Unknown" || "$manufacturer" == "UNKNOWN" || ${#manufacturer} -gt 20 ]]; then
    echo "  Skipping - invalid manufacturer" >&2
    exit 0
fi

# Step 3: Extract model
model=$(echo -n "In this gallery of photos from a $device_type made by $manufacturer: $title

What is the model name? Reply with ONLY the model (no manufacturer).
Examples: EOS R5, iPhone 15, Pixel 8, X-T5, a7IV

Answer:" | ollama run "$MODEL" 2>/dev/null | grep -v '^$' | tail -1 | xargs)

echo "  Model: $model" >&2

# Check if model is valid
if [[ -z "$model" || "$model" == "Unknown" || "$model" == "UNKNOWN" || ${#model} -gt 30 ]]; then
    echo "  Skipping - invalid model" >&2
    exit 0
fi

# Check if model contains lens patterns (mm, F/, f/)
if [[ "$model" =~ mm || "$model" =~ [Ff][0-9] || "$model" =~ -[0-9]+-[0-9]+ ]]; then
    echo "  Skipping - appears to be a lens: $model" >&2
    exit 0
fi

# Clean up - make path safe
manufacturer="${manufacturer// /_}"
manufacturer="${manufacturer//\//_}"
manufacturer="${manufacturer//[^a-zA-Z0-9_-]/}"

model="${model// /_}"
model="${model//\//_}"
model="${model//[^a-zA-Z0-9_-]/}"

# Output the full params line
echo "device/$manufacturer/$model.jpg $url"

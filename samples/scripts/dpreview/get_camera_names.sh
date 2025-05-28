#!/bin/bash

# Read gallery title from stdin, output Manufacturer/Model format
read -r title

# Extract manufacturer
manufacturer=$(echo -n "Extract the camera manufacturer from this title: $title

Rules:
- Output ONLY the manufacturer name, nothing else
- Use proper capitalization: Canon, Nikon, Sony, Olympus, Fujifilm, Panasonic, etc.
- For 'Fuji' use 'Fujifilm'
- For phone brands like 'OnePlus' keep as is
- If no clear manufacturer, output 'Unknown'

Output:" | ollama run llama3 2>/dev/null | grep -v "The extracted" | head -1 | xargs)

# Extract model
model=$(echo -n "Extract the camera model from this title: $title

Rules:
- Output ONLY the model name/number, nothing else
- Do NOT include the manufacturer name
- Replace spaces with hyphens
- Replace special characters like * with hyphens
- If unclear, use the most specific part after the manufacturer

Examples:
- 'Canon EOS 5D' -> 'EOS-5D'
- 'Sony a6500' -> 'a6500'
- 'OnePlus 5' -> '5'

Output:" | ollama run llama3 2>/dev/null | grep -v "The extracted" | head -1 | xargs)

# Validate and clean up
if [[ -z "$manufacturer" || "$manufacturer" == *"extracted"* || "$manufacturer" == *":"* ]]; then
    manufacturer="Unknown"
fi

if [[ -z "$model" || "$model" == *"extracted"* || "$model" == *":"* || "$model" == *"->"* ]]; then
    model="Model"
fi

# Combine them
camera_info="${manufacturer}/${model}"

# Replace any problematic characters
camera_info="${camera_info//\*/-}"
camera_info="${camera_info// /-}"
camera_info="${camera_info//->/-}"

# Output the result
echo "$camera_info"
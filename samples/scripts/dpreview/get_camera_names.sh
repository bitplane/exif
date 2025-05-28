#!/bin/bash

# Read gallery title from stdin, output Manufacturer/Model format
read -r title

# Extract manufacturer
manufacturer=$(echo -n "You are a camera manufacturer extractor. Extract ONLY the camera manufacturer/brand name from: $title
Use the full brand name.
Examples: Canon, Nikon, Sony, Olympus, Fujifilm, Panasonic, Kodak, Casio, Samsung
Note: 'Fuji' should be 'Fujifilm'
Output only the manufacturer name:" | ollama run llama3 | head -1 | xargs)

# Extract model
model=$(echo -n "You are a camera model extractor. Extract ONLY the camera model name from: $title
Do NOT include the manufacturer name in the model.
Replace spaces with hyphens.
Replace asterisks (*) with hyphens.
Examples: 
- 'Nikon D850' -> 'D850'
- 'Canon EOS 5D' -> 'EOS-5D'
- 'Sony DSC-HX200V' -> 'DSC-HX200V'
- 'Olympus PEN-F' -> 'PEN-F'
- 'Pentax *ist D' -> '-ist-D'
Output only the model:" | ollama run llama3 | head -1 | xargs)

# Combine them
camera_info="${manufacturer}/${model}"

# Replace any asterisks with hyphens in the final result
camera_info="${camera_info//\*/-}"

# Output the result
echo "$camera_info"
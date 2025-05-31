#!/usr/bin/env python3
"""
Generate Makefile rules from multiple params files
Uses normalization function to handle duplicates
Order is determined by command line argument order
"""

import sys
import os
from collections import OrderedDict

def normalize_path(source_name, path):
    """
    Normalize a path for deduplication.
    This function will evolve as we learn more about the data.
    
    Args:
        source_name: The name of the source (e.g., 'dpreview', 'wikimedia')
        path: The file path (e.g., 'device/Canon-EOS-R5.jpg')
    
    Returns:
        Normalized path for comparison
    """
    # For now, just lowercase normalization
    # We can add more sophisticated logic as we analyze the data:
    # - Handle different naming conventions (spaces, dashes, underscores)
    # - Extract camera model from different path structures
    # - Handle manufacturer name variations
    return path.lower()

def parse_params_file(params_file, source_name):
    """Parse a params file and return list of (target, command) tuples"""
    rules = []
    
    if not os.path.exists(params_file):
        return rules
    
    with open(params_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split into filename and args
            parts = line.split(' ', 1)
            if len(parts) < 2:
                continue
            
            filename, args = parts
            target = f"data/{filename}"
            
            # Build the full command
            command = f"./scripts/{source_name}/download.sh $@ {args}"
            
            rules.append((target, command, source_name))
    
    return rules

def main():
    if len(sys.argv) < 2:
        print("Usage: build_makefile.py <downloader1> [downloader2] ...", file=sys.stderr)
        sys.exit(1)
    
    downloaders = sys.argv[1:]
    
    # Use OrderedDict to maintain order while deduplicating
    # First occurrence wins (based on command line order)
    targets = OrderedDict()
    
    # Process in order - first one wins
    for downloader in downloaders:
        params_file = f".cache/{downloader}.params"
        rules = parse_params_file(params_file, downloader)
        
        for target, command, source in rules:
            # Extract the path part after "data/"
            path = target[5:] if target.startswith("data/") else target
            norm_key = normalize_path(source, path)
            
            # First occurrence wins
            if norm_key not in targets:
                targets[norm_key] = (target, command, source)
    
    # Generate makefile
    print("# Generated Makefile from params files")
    print(f"# Sources: {', '.join(downloaders)} (in priority order)")
    print()
    
    # Output rules in order of first occurrence
    for norm_key, (target, command, source) in targets.items():
        # Escape special characters in Make
        escaped_target = target.replace('$', '$$')
        
        print(f"{escaped_target}:")
        print(f"\t@mkdir -p $(dir $@)")
        print(f"\t{command}")
        print(f"# Source: {source}")
        print()

if __name__ == '__main__':
    main()
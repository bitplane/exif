#!/usr/bin/env python3
"""
Generate Makefile rules from multiple params files
Uses normalization function to handle duplicates
Order is determined by command line argument order
"""

import sys
import os
import re
import json
import argparse
from collections import OrderedDict

# Load filters on startup
IGNORE_FILTERS = []
REPLACE_FILTERS = []
FILTERS_FILE = os.path.join(os.path.dirname(__file__), 'filters.json')
if os.path.exists(FILTERS_FILE):
    try:
        with open(FILTERS_FILE, 'r') as f:
            filter_data = json.load(f)
            IGNORE_FILTERS = filter_data.get("files", {}).get("ignore", [])
            REPLACE_FILTERS = filter_data.get("files", {}).get("replace", [])
    except Exception:
        IGNORE_FILTERS = []
        REPLACE_FILTERS = []

def normalize_path(source_name, path):
    """
    Normalize a path for deduplication.
    Returns (normalized_path, applied_filters) tuple
    """ 
    applied_filters = []
    current_path = path
    
    # Apply replacements first (can cascade)
    for find_pattern, replace_with in REPLACE_FILTERS:
        try:
            new_path = re.sub(find_pattern, replace_with, current_path)
            if new_path != current_path:
                applied_filters.append(("replace", find_pattern, replace_with))
                current_path = new_path
        except re.error:
            pass  # Invalid regex, skip
    
    # Then check ignore filters on the final result
    for filter_pattern in IGNORE_FILTERS:
        try:
            if re.search(filter_pattern, current_path):
                applied_filters.append(("ignore", filter_pattern))
                return "", applied_filters  # Filtered out
        except re.error:
            pass  # Invalid regex, skip
    
    return current_path, applied_filters

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

def generate_targets_dict(downloaders):
    """Generate the targets dictionary from downloaders list"""
    # Use OrderedDict to maintain order while collecting all sources per target
    targets = OrderedDict()
    
    # Collect all sources for each normalized target
    for downloader in downloaders:
        params_file = f".cache/{downloader}.params"
        rules = parse_params_file(params_file, downloader)
        
        for target, command, source in rules:
            # Extract the path part after "data/"
            path = target[5:] if target.startswith("data/") else target
            norm_key, applied_filters = normalize_path(source, path)
            
            # Skip if filtered out (falsey)
            if not norm_key:
                continue
            
            # Collect all sources for this target
            if norm_key not in targets:
                targets[norm_key] = []

            targets[norm_key].append((target, command, source, applied_filters))
    
    return targets

def main():
    parser = argparse.ArgumentParser(description='Generate Makefile rules from params files')
    parser.add_argument('downloaders', nargs='+', help='Downloader names (e.g. dpreview wikimedia)')
    parser.add_argument('--dump', action='store_true', help='Dump JSON instead of Makefile')
    
    args = parser.parse_args()
    
    targets = generate_targets_dict(args.downloaders)
    
    if args.dump:
        # JSON dump mode - convert to serializable format
        dump_data = {
            'targets': {},
            'filters': {
                'ignore': IGNORE_FILTERS,
                'replace': REPLACE_FILTERS
            }
        }
        for norm_key, sources in targets.items():
            source_list = []
            for target, command, source, applied_filters in sources:
                source_list.append({
                    'target': target,
                    'source': source,
                    'applied_filters': applied_filters
                })
            dump_data['targets'][norm_key] = source_list
        print(json.dumps(dump_data, indent=2))
        return
    
    # Generate makefile
    print("# Generated Makefile from params files")
    print(f"# Sources: {', '.join(args.downloaders)} (in priority order)")
    print()
    
    # Collect directory dependencies
    dir_deps = {}
    
    # Output rules with all sources grouped by target
    for norm_key, sources in targets.items():
        # Use the first target path (they should all be equivalent after normalization)
        target = sources[0][0]
        escaped_target = target.replace('$', '$$')
        
        # Track directory dependencies
        parent_dir = os.path.dirname(target)
        if parent_dir and parent_dir != 'data':
            if parent_dir not in dir_deps:
                dir_deps[parent_dir] = []
            dir_deps[parent_dir].append(target)
        
        print(f"{escaped_target}: scripts/filters.json")
        print(f"\t@mkdir -p $(dir $@)")
        
        if len(sources) == 1:
            # Single source - simple rule
            _, command, source = sources[0]
            print(f"\t{command}")
            print(f"# Source: {source}")
        else:
            # Multiple sources - try in order until one succeeds
            print(f"# Sources: {', '.join(s[2] for s in sources)}")
            for i, (_, command, source) in enumerate(sources):
                if i < len(sources) - 1:
                    print(f"\t{command} || \\")
                else:
                    print(f"\t{command}")
        
        print()
    
    # Output directory targets
    print("# Directory targets")
    if dir_deps:
        # Make all directories phony targets
        phony_dirs = ' '.join(d.replace('$', '$$') for d in sorted(dir_deps.keys()))
        print(f".PHONY: {phony_dirs}")
        print()
        
        for directory in sorted(dir_deps.keys()):
            escaped_dir = directory.replace('$', '$$')
            deps = ' '.join(dep.replace('$', '$$') for dep in sorted(dir_deps[directory]))
            
            print(f"{escaped_dir}: {deps}")
            print(f"\t@echo \"Downloaded {len(dir_deps[directory])} files to {directory}\"")
            print()

if __name__ == '__main__':
    main()

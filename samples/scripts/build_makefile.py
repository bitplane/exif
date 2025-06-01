#!/usr/bin/env python3
"""
Generate Makefile rules from multiple params files
Uses normalization function to handle duplicates
Order is determined by command line argument order
"""

import sys
import os
import json
import argparse
from collections import OrderedDict

# Add editor modules to path
editor_path = os.path.join(os.path.dirname(__file__), 'editor')
sys.path.insert(0, editor_path)

# Import using absolute paths
import images.file_list
import filters.base

FileList = images.file_list.FileList
load_filters_from_json = filters.base.load_filters_from_json

# Load filters on startup
FILTERS_FILE = os.path.join(os.path.dirname(__file__), 'filters.json')
FILTERS = []
if os.path.exists(FILTERS_FILE):
    try:
        with open(FILTERS_FILE, 'r') as f:
            filter_data = json.load(f)
            FILTERS = load_filters_from_json(filter_data)
    except Exception:
        FILTERS = []


def generate_targets_dict(downloaders):
    """Generate the targets dictionary from downloaders list"""
    # Create file list and load data
    file_list = FileList()
    file_list.load()
    
    # Apply filters
    filtered_data = file_list.apply_filters(FILTERS)
    
    # Convert to old format for compatibility
    targets = OrderedDict()
    
    for norm_key, sources in filtered_data.items():
        if norm_key not in targets:
            targets[norm_key] = []
        
        for source_info in sources:
            target = f"data/{norm_key}"
            source = source_info["source"]
            args = source_info["args"]
            command = f"./scripts/{source}/download.sh $@ {args}"
            
            # Convert applied_filters to old format
            applied_filters = []
            for f in source_info["applied_filters"]:
                filter_type = f["type"]
                if "Ignore:" in filter_type:
                    # Extract pattern from "Ignore: pattern" format
                    pattern = filter_type.split("Ignore: ", 1)[1]
                    applied_filters.append(("ignore", pattern))
                elif "Replace:" in filter_type:
                    # For replace, we have from/to info
                    applied_filters.append(("replace", f["from"], f["to"]))
            
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
                'ignore': [f.pattern for f in FILTERS if hasattr(f, 'pattern')],
                'replace': [[f.find, f.replace] for f in FILTERS if hasattr(f, 'find')]
            },
            'filters_applied': 0
        }
        total_filters_applied = 0
        for norm_key, sources in targets.items():
            source_list = []
            for target, command, source, applied_filters in sources:
                total_filters_applied += len(applied_filters)
                source_list.append({
                    'target': target,
                    'source': source,
                    'applied_filters': applied_filters
                })
            dump_data['targets'][norm_key] = source_list
        dump_data['filters_applied'] = total_filters_applied
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

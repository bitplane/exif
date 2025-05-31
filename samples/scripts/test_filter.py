#!/usr/bin/env python3
"""
Interactive test for the filtering system.
Imports the generate_targets_dict function and prints normalized file paths.
"""

import os
import glob
from build_makefile import generate_targets_dict

def main():
    # Auto-discover downloaders from .cache/*.params files
    params_files = glob.glob('.cache/*.params')
    downloaders = [os.path.basename(f).replace('.params', '') for f in params_files]
    
    if not downloaders:
        print("No .params files found in .cache/")
        return
    
    targets = generate_targets_dict(downloaders)
    
    # Color codes for different sources
    colors = {
        'dpreview': '\033[32m',    # Green
        'wikimedia': '\033[34m',   # Blue
        'flickr': '\033[35m',      # Magenta
        'unsplash': '\033[36m',    # Cyan
        'default': '\033[33m'      # Yellow
    }
    reset = '\033[0m'
    
    # Collect and sort entries
    entries = []
    for norm_key, sources in targets.items():
        # Get the first target path (they should all be equivalent after normalization)
        target = sources[0][0]
        path = target[5:] if target.startswith("data/") else target
        
        # Build colored source list
        source_names = [s[2] for s in sources]
        colored_sources = []
        for source in source_names:
            color = colors.get(source, colors['default'])
            colored_sources.append(f"{color}{source}{reset}")
        
        # Primary source is first one (highest priority)
        primary_source = source_names[0] if source_names else 'unknown'
        primary_color = colors.get(primary_source, colors['default'])
        
        entries.append((primary_source, f"{primary_color}{primary_source:<10}{reset}", norm_key, ', '.join(source_names)))
    
    # Sort by primary source, then by path
    entries.sort(key=lambda x: (x[0], x[2]))
    
    # Print header
    print(f"{'SOURCE':<12} {'PATH':<50} SOURCES")
    print(f"{'-' * 12} {'-' * 50} {'-' * 20}")
    
    # Print sorted entries
    for _, colored_source, path, all_sources in entries:
        path_display = path[:48] + '..' if len(path) > 50 else path
        print(f"{colored_source} {path_display:<50} {all_sources}")

if __name__ == '__main__':
    main()

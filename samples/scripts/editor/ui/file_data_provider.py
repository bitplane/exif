"""
Data provider for the files table that wraps FileList with formatting
"""

import hashlib
from functools import lru_cache
from typing import List, Tuple


COLOURS = ["red", "green", "yellow", "blue", "magenta", "cyan",
           "bright_red", "bright_green", "bright_yellow", 
           "bright_blue", "bright_magenta", "bright_cyan",
          ]

@lru_cache
def get_colour(name: str) -> str:
    """
    Get a stable colour representation given a name
    """
    hash_value = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    idx = hash_value % len(COLOURS)
    return COLOURS[idx]


class FileDataProvider:
    """Wraps FileList to provide formatted data for the table"""
    
    def __init__(self, file_list):
        self.file_list = file_list
    
    def __len__(self):
        """Number of rows"""
        return len(self.file_list)
    
    def __getitem__(self, index: int) -> Tuple[str, str]:
        """Get formatted row data: (path, colored_sources)"""
        key, path, sources_str = self.file_list[index]
        
        # Color based on first source
        priority_source = sources_str.split(", ")[0] if sources_str else "unknown"
        source_colour =  get_colour(priority_source)
        coloured_sources = f"[{source_colour}]{sources_str}[/]"
        return (path, coloured_sources)
    
    def get_version(self):
        """Get current data version"""
        return self.file_list.get_version()
    
    def format_row(self, index: int) -> Tuple[str, str]:
        """Format a row for display"""
        return self[index]

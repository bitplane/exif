#!/usr/bin/env python3
"""
Interactive filter browser using Textual
Watches build_makefile.py for changes and live-reloads
"""

import os
import importlib
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Set, Dict
from bisect import bisect_left

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header
from textual.binding import Binding
from textual.reactive import reactive

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))
import build_makefile


class FilterBrowser(App):
    """Interactive browser for filter results"""
    
    CSS = """
    DataTable {
        height: 100%;
    }
    DataTable > .datatable--header {
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
    ]
    
    watch_file = Path(__file__).parent / "build_makefile.py"
    last_mtime = 0.0
    
    # State tracking for incremental updates
    current_entries: Set[Tuple[str, str]] = set()  # (norm_key, sources_str)
    sorted_keys: List[str] = []  # Sorted list of norm_keys
    key_to_row: Dict[str, int] = {}  # Map norm_key to row index
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the data table"""
        table = self.query_one(DataTable)
        table.add_columns("Path", "Sources")
        table.cursor_type = "row"
        self.load_data()
        self.set_interval(0.5, self.check_file_changes)
    
    def check_file_changes(self) -> None:
        """Check for file changes"""
        try:
            current_mtime = self.watch_file.stat().st_mtime
            if current_mtime > self.last_mtime:
                self.last_mtime = current_mtime
                self.reload_module()
        except Exception:
            pass
    
    def reload_module(self) -> None:
        """Reload the build_makefile module"""
        try:
            importlib.reload(build_makefile)
            self.load_data()
            self.notify("Reloaded build_makefile.py")
        except Exception as e:
            self.notify(f"Reload error: {e}", severity="error")
    
    def load_data(self) -> None:
        """Load and display the filtered data"""
        table = self.query_one(DataTable)
        table.clear()
        
        # Auto-discover downloaders from .cache/*.params files
        import glob
        params_files = glob.glob('.cache/*.params')
        downloaders = [os.path.basename(f).replace('.params', '') for f in params_files]
        
        if not downloaders:
            table.add_row("No .params files found in .cache/", "")
            return
        
        # Get the targets
        try:
            targets = build_makefile.generate_targets_dict(downloaders)
        except Exception as e:
            table.add_row(f"Error in generate_targets_dict: {str(e)}", "")
            table.add_row("Fix build_makefile.py and it will reload", "")
            return
        
        # Color codes for sources
        colors = {
            'dpreview': 'green',
            'wikimedia': 'blue',
            'flickr': 'magenta',
            'unsplash': 'cyan',
        }
        
        # Collect and sort entries
        entries = []
        for norm_key, sources in targets.items():
            # Get the first target path
            target = sources[0][0]
            path = target[5:] if target.startswith("data/") else target
            
            # Get source names
            source_names = [s[2] for s in sources]
            primary_source = source_names[0] if source_names else 'unknown'
            
            # Format sources with primary in color
            if len(source_names) == 1:
                source_color = colors.get(primary_source, 'yellow')
                sources_str = f"[{source_color}]{primary_source}[/]"
            else:
                # Show all sources, primary in color
                other_sources = ', '.join(source_names[1:])
                source_color = colors.get(primary_source, 'yellow')
                sources_str = f"{other_sources}, [{source_color}]{primary_source}[/]"
            
            entries.append((norm_key, sources_str))
        
        # Sort by normalized key
        entries.sort(key=lambda x: x[0])
        
        # Add to table
        for norm_key, sources_str in entries:
            # Show normalized path
            table.add_row(norm_key, sources_str)
    
    def action_reload(self) -> None:
        """Manual reload action"""
        self.reload_module()
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


if __name__ == "__main__":
    app = FilterBrowser()
    app.run()
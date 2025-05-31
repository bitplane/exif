#!/usr/bin/env python3
"""
Interactive filter browser using Textual with filter management
Uses subprocess to call build_makefile.py for better isolation
"""

import os
import json
import subprocess
import glob
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Set, Dict
from bisect import bisect_left

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Label, Input, TabbedContent, TabPane
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import ModalScreen


class FilterEditModal(ModalScreen):
    """Modal dialog for editing filter patterns"""
    
    CSS = """
    FilterEditModal {
        align: center middle;
    }
    
    FilterEditModal > Container {
        width: 60;
        height: 11;
        border: thick $background;
        background: $surface;
    }
    
    FilterEditModal Label {
        margin: 1 2;
    }
    
    FilterEditModal Input {
        margin: 0 2 1 2;
    }
    """
    
    def __init__(self, initial_value: str = "", title: str = "Add Filter"):
        super().__init__()
        self.initial_value = initial_value
        self.title = title
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title)
            yield Input(value=self.initial_value, placeholder="Enter regex pattern...")
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class FilterBrowser(App):
    """Interactive browser for filter results with filter management"""
    
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
        Binding("delete", "add_filter", "Add Filter", show=True),
        Binding("ctrl+t", "toggle_tab", "Switch Tab"),
    ]
    
    watch_files = [
        Path(__file__).parent / "build_makefile.py",
        Path(__file__).parent / "filters.json"
    ]
    last_mtimes = {}
    
    # State tracking for incremental updates
    current_entries: Set[Tuple[str, str]] = set()
    sorted_keys: List[str] = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(initial="files"):
            with TabPane("Files", id="files"):
                files_table = DataTable(id="files_table")
                yield files_table
                
            with TabPane("Filters", id="filters"):
                filters_table = DataTable(id="filters_table")
                yield filters_table
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the data tables"""
        # Set up files table
        files_table = self.query_one("#files_table", DataTable)
        terminal_width = self.size.width
        path_width = int(terminal_width * 0.7)
        sources_width = terminal_width - path_width - 3
        
        files_table.add_column("Path", width=path_width)
        files_table.add_column("Sources", width=sources_width)
        files_table.cursor_type = "row"
        
        # Set up filters table
        filters_table = self.query_one("#filters_table", DataTable)
        filters_table.add_column("Filter Pattern", width=terminal_width - 10)
        filters_table.cursor_type = "row"
        
        # Load initial data
        self.load_files_data()
        self.load_filters_data()
        
        # Start checking for file changes
        self.set_interval(0.5, self.check_file_changes)
    
    def check_file_changes(self) -> None:
        """Check for file changes"""
        for watch_file in self.watch_files:
            try:
                current_mtime = watch_file.stat().st_mtime
                if current_mtime > self.last_mtimes.get(watch_file, 0):
                    self.last_mtimes[watch_file] = current_mtime
                    if watch_file.name == "build_makefile.py":
                        self.load_files_data()
                        self.notify("Reloaded build_makefile.py")
                    elif watch_file.name == "filters.json":
                        self.load_filters_data()
                        self.notify("Reloaded filters.json")
            except Exception:
                pass
    
    def load_files_data(self) -> None:
        """Load file data using subprocess"""
        table = self.query_one("#files_table", DataTable)
        
        # Auto-discover downloaders
        params_files = glob.glob('.cache/*.params')
        downloaders = [os.path.basename(f).replace('.params', '') for f in params_files]
        
        if not downloaders:
            if not self.current_entries:
                table.clear()
                table.add_row("No .params files found in .cache/", "")
            return
        
        # Call build_makefile.py with --dump
        try:
            result = subprocess.run(
                ['python3', './scripts/build_makefile.py', '--dump'] + downloaders,
                capture_output=True,
                text=True,
                check=True
            )
            targets = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"Error running build_makefile.py: {e}", "")
            if e.stderr:
                table.add_row(e.stderr.strip(), "")
            return
        except json.JSONDecodeError as e:
            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"JSON decode error: {e}", "")
            return
        
        # Terminal colors
        good_colors = [
            'red', 'green', 'yellow', 'blue', 'magenta', 'cyan',
            'bright_red', 'bright_green', 'bright_yellow', 
            'bright_blue', 'bright_magenta', 'bright_cyan',
        ]
        
        # Build new entries
        new_entries = set()
        new_entry_details = {}
        
        for norm_key, sources in targets.items():
            if not sources:
                continue
                
            # Get source names
            source_names = [s['source'] for s in sources]
            primary_source = source_names[0] if source_names else 'unknown'
            
            # Get color using hash
            color_index = hash(primary_source) % len(good_colors)
            source_color = good_colors[color_index]
            
            # Color the path
            colored_path = f"[{source_color}]{norm_key}[/]"
            
            # Format sources
            sources_str = ', '.join(source_names)
            
            entry = (norm_key, sources_str)
            new_entries.add(entry)
            new_entry_details[norm_key] = (colored_path, sources_str)
        
        # Simple update - just rebuild the table
        if new_entries != self.current_entries:
            table.clear()
            self.current_entries = new_entries
            self.sorted_keys = sorted([k for k, _ in new_entries])
            
            for norm_key in self.sorted_keys:
                if norm_key in new_entry_details:
                    colored_path, sources = new_entry_details[norm_key]
                    table.add_row(colored_path, sources, key=norm_key)
    
    def load_filters_data(self) -> None:
        """Load filter patterns from filters.json"""
        table = self.query_one("#filters_table", DataTable)
        table.clear()
        
        try:
            with open('./scripts/filters.json', 'r') as f:
                filters = json.load(f)
                
            for pattern in filters:
                table.add_row(pattern, key=pattern)
                
            if not filters:
                table.add_row("(No filters - press DEL on a file to add)", key="_empty")
        except Exception as e:
            table.add_row(f"Error loading filters: {e}", key="_error")
    
    def action_add_filter(self) -> None:
        """Add a filter based on selected file"""
        # Check which tab is active
        tabbed_content = self.query_one(TabbedContent)
        
        if tabbed_content.active == "files":
            # Add filter from selected file
            table = self.query_one("#files_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return
                
            row_key = table.get_row_at(table.cursor_row)[0]
            if row_key:
                # Create regex-safe version
                safe_pattern = re.escape(str(row_key))
                self.push_screen(FilterEditModal(safe_pattern, "Add Filter"), self._add_filter_callback)
        
        elif tabbed_content.active == "filters":
            # Edit or delete selected filter
            table = self.query_one("#filters_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return
            
            row = table.get_row_at(table.cursor_row)
            if row and len(row) > 0 and row[0] != "(No filters - press DEL on a file to add)":
                # Remove the filter
                self._remove_filter(str(row[0]))
    
    def _add_filter_callback(self, pattern: str) -> None:
        """Callback for adding a filter"""
        if not pattern:
            return
            
        try:
            # Load current filters
            with open('./scripts/filters.json', 'r') as f:
                filters = json.load(f)
            
            # Add new filter if not already present
            if pattern not in filters:
                filters.append(pattern)
                
                # Save back
                with open('./scripts/filters.json', 'w') as f:
                    json.dump(filters, f, indent=2)
                    
                self.notify(f"Added filter: {pattern}")
                self.load_filters_data()
                self.load_files_data()  # Reload files to apply filter
        except Exception as e:
            self.notify(f"Error adding filter: {e}", severity="error")
    
    def _remove_filter(self, pattern: str) -> None:
        """Remove a filter"""
        try:
            # Load current filters
            with open('./scripts/filters.json', 'r') as f:
                filters = json.load(f)
            
            # Remove filter
            if pattern in filters:
                filters.remove(pattern)
                
                # Save back
                with open('./scripts/filters.json', 'w') as f:
                    json.dump(filters, f, indent=2)
                    
                self.notify(f"Removed filter: {pattern}")
                self.load_filters_data()
                self.load_files_data()  # Reload files to update
        except Exception as e:
            self.notify(f"Error removing filter: {e}", severity="error")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in filters table for editing"""
        if event.data_table.id == "filters_table":
            row = event.data_table.get_row_at(event.cursor_row)
            if row and len(row) > 0 and row[0] != "(No filters - press DEL on a file to add)":
                # Edit the filter
                pattern = str(row[0])
                self.push_screen(FilterEditModal(pattern, "Edit Filter"), 
                               lambda new_pattern: self._edit_filter(pattern, new_pattern))
    
    def _edit_filter(self, old_pattern: str, new_pattern: str) -> None:
        """Edit an existing filter"""
        if not new_pattern or old_pattern == new_pattern:
            return
            
        try:
            # Load current filters
            with open('./scripts/filters.json', 'r') as f:
                filters = json.load(f)
            
            # Replace old with new
            if old_pattern in filters:
                idx = filters.index(old_pattern)
                filters[idx] = new_pattern
                
                # Save back
                with open('./scripts/filters.json', 'w') as f:
                    json.dump(filters, f, indent=2)
                    
                self.notify(f"Updated filter: {old_pattern} → {new_pattern}")
                self.load_filters_data()
                self.load_files_data()
        except Exception as e:
            self.notify(f"Error editing filter: {e}", severity="error")
    
    def action_toggle_tab(self) -> None:
        """Toggle between tabs"""
        tabbed_content = self.query_one(TabbedContent)
        if tabbed_content.active == "files":
            tabbed_content.active = "filters"
        else:
            tabbed_content.active = "files"
    
    def action_reload(self) -> None:
        """Manual reload"""
        self.load_files_data()
        self.load_filters_data()
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


if __name__ == "__main__":
    app = FilterBrowser()
    app.run()
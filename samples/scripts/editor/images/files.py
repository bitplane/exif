"""
Files table widget
"""

import os
import json
import subprocess
import glob
import re
from textual.widgets import DataTable
from textual.binding import Binding
from .modals import IgnoreFilterModal, ReplaceFilterModal


class FilesTable(DataTable):
    """Files table with specific bindings"""
    
    BINDINGS = [
        Binding("delete", "ignore_filter", "Ignore", show=True),
        Binding("f2", "replace_filter", "Replace", show=True),
    ]
    
    def action_ignore_filter(self):
        self.app.action_ignore_filter()
    
    def action_replace_filter(self):
        self.app.action_replace_filter()


class FilesWidget:
    """Widget for managing the files display"""
    
    def __init__(self, editor_app):
        self.editor_app = editor_app
        self.current_entries = set()
        self.sorted_keys = []
    
    def setup_table(self, table: FilesTable, terminal_width: int):
        """Initialize the files table"""
        path_width = int(terminal_width * 0.7)
        sources_width = terminal_width - path_width - 3
        
        table.add_column("Path", width=path_width)
        table.add_column("Sources", width=sources_width)
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        return path_width, sources_width
    
    def load_data(self, table: FilesTable, log_writer):
        """Load file data using subprocess"""
        log_writer("Loading files data...")
        
        # Auto-discover downloaders
        params_files = glob.glob(".cache/*.params")
        downloaders = [os.path.basename(f).replace(".params", "") for f in params_files]
        log_writer(f"Found downloaders: {downloaders}", "debug")

        if not downloaders:
            log_writer("No .params files found in .cache/", "warning")
            if not self.current_entries:
                table.clear()
                table.add_row("No .params files found in .cache/", "")
            return

        # Call build_makefile.py with --dump
        cmd = ["python3", "./scripts/build_makefile.py", "--dump"] + downloaders
        log_writer(f"Running command: {' '.join(cmd)}", "debug")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            log_writer(f"Command returned {len(result.stdout)} bytes", "debug")

            if result.stderr:
                log_writer(f"Stderr: {result.stderr}", "warning")

            data = json.loads(result.stdout)
            targets = data['targets']
            filters_applied = data.get('filters_applied', 0)
            log_writer(f"Parsed {len(targets)} targets from JSON ({filters_applied} filters applied)", "info")

        except subprocess.CalledProcessError as e:
            log_writer(f"Error running build_makefile.py: {e}", "error")
            log_writer(f"Return code: {e.returncode}", "error")
            if e.stderr:
                log_writer(f"Stderr: {e.stderr}", "error")
            if e.stdout:
                log_writer(f"Stdout: {e.stdout[:200]}...", "debug")

            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"Error running build_makefile.py: {e}", "")
            if e.stderr:
                table.add_row(e.stderr.strip(), "")
            return

        except json.JSONDecodeError as e:
            log_writer(f"JSON decode error: {e}", "error")
            log_writer(f"Raw output: {result.stdout[:200]}...", "debug")

            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"JSON decode error: {e}", "")
            return

        # Terminal colors
        good_colors = [
            "red", "green", "yellow", "blue", "magenta", "cyan",
            "bright_red", "bright_green", "bright_yellow", 
            "bright_blue", "bright_magenta", "bright_cyan",
        ]

        # Build new entries
        new_entries = set()
        new_entry_details = {}

        log_writer(f"Processing {len(targets)} target entries", "debug")

        for norm_key, sources in targets.items():
            if not sources:
                continue

            # Get source names
            source_names = [s["source"] for s in sources]
            primary_source = source_names[0] if source_names else "unknown"

            # Get color using hash
            color_index = hash(primary_source) % len(good_colors)
            source_color = good_colors[color_index]

            # Color the path
            colored_path = f"[{source_color}]{norm_key}[/]"

            # Format sources
            sources_str = ", ".join(source_names)

            entry = (norm_key, sources_str)
            new_entries.add(entry)
            new_entry_details[norm_key] = (colored_path, sources_str)

        log_writer(f"Built {len(new_entries)} display entries", "info")

        # Simple update - just rebuild the table
        if new_entries != self.current_entries:
            log_writer(
                f"Updating table (was {len(self.current_entries)}, now {len(new_entries)} entries)",
                "debug",
            )
            table.clear()
            self.current_entries = new_entries
            self.sorted_keys = sorted([k for k, _ in new_entries])

            for norm_key in self.sorted_keys:
                if norm_key in new_entry_details:
                    colored_path, sources = new_entry_details[norm_key]
                    table.add_row(colored_path, sources, key=norm_key)

            log_writer(f"Table updated with {table.row_count} rows", "info")
        else:
            log_writer("No changes detected in entries", "debug")
    
    def get_selected_file(self, table: FilesTable):
        """Get the currently selected file path"""
        if table.row_count == 0 or table.cursor_row is None:
            return None
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            return str(row_key) if row_key else None
        except Exception:
            return None
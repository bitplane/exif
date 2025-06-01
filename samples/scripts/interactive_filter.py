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
from typing import List, Tuple, Set

from textual.app import App, ComposeResult
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Input,
    TabbedContent,
    TabPane,
    RichLog,
    Static,
)
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import ModalScreen


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


class IgnoreTable(DataTable):
    """Ignore patterns table with specific bindings"""
    
    BINDINGS = [
        Binding("delete", "delete_pattern", "Delete", show=True),
        Binding("enter", "edit_pattern", "Edit", show=True),
    ]
    
    def action_delete_pattern(self):
        self.app.action_delete_ignore_pattern()
    
    def action_edit_pattern(self):
        self.app.action_edit_ignore_pattern()


class ReplaceTable(DataTable):
    """Replace patterns table with specific bindings"""
    
    BINDINGS = [
        Binding("delete", "delete_pattern", "Delete", show=True),
        Binding("enter", "edit_pattern", "Edit", show=True),
    ]
    
    def action_delete_pattern(self):
        self.app.action_delete_replace_pattern()
    
    def action_edit_pattern(self):
        self.app.action_edit_replace_pattern()


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
    
    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.prevent_default()


class ReplaceEditModal(ModalScreen):
    """Modal dialog for editing replace patterns"""

    CSS = """
    ReplaceEditModal {
        align: center middle;
    }
    
    ReplaceEditModal > Container {
        width: 70;
        height: 15;
        border: thick $background;
        background: $surface;
    }
    
    ReplaceEditModal Label {
        margin: 1 2;
    }
    
    ReplaceEditModal Input {
        margin: 0 2 1 2;
    }
    """

    def __init__(self, find_pattern: str = "", replace_pattern: str = ""):
        super().__init__()
        self.find_pattern = find_pattern
        self.replace_pattern = replace_pattern

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Replace Pattern")
            yield Input(value=self.find_pattern, placeholder="Find regex pattern...", id="find_input")
            yield Label("Replace With")
            yield Input(value=self.replace_pattern, placeholder="Replacement text...", id="replace_input")

    def on_mount(self) -> None:
        self.query_one("#find_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "find_input":
            # Move to replace input
            self.query_one("#replace_input", Input).focus()
        else:
            # Submit the form
            find_val = self.query_one("#find_input", Input).value
            replace_val = self.query_one("#replace_input", Input).value
            self.dismiss((find_val, replace_val))
    
    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.prevent_default()


def save_filters(filter_data: dict) -> None:
    """Save filter configuration to JSON file"""
    temp_file = "./scripts/filters.json.tmp"
    with open(temp_file, "w") as f:
        json.dump(filter_data, f, indent=2)
    os.rename(temp_file, "./scripts/filters.json")

def load_filters() -> dict:
    """Load filter configuration from JSON file"""
    try:
        with open("./scripts/filters.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"files": {"ignore": [], "replace": []}}


class FilterBrowser(App):
    """Interactive browser for filter results with filter management"""

    CSS = """
    DataTable {
        height: 100%;
        border: solid $accent;
    }
    DataTable > .datatable--header {
        text-style: bold;
    }
    RichLog {
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f5", "reload", "Reload", show=True),
        Binding("ctrl+r", "reload", "Reload", show=False),
    ]

    watch_files = [
        Path(__file__).parent / "build_makefile.py",
        Path(__file__).parent / "filters.json",
    ]
    last_mtimes = {}

    # State tracking for incremental updates
    current_entries: Set[Tuple[str, str]] = set()
    sorted_keys: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header()

        # Use the with syntax which is the correct pattern for TabbedContent
        with TabbedContent(initial="files") as tabbed_content:
            with TabPane("Files", id="files"):
                with Container():
                    yield FilesTable(id="files_table")

            with TabPane("Replace", id="replace"):
                with Container():
                    yield ReplaceTable(id="replace_table")

            with TabPane("Ignore", id="ignore"):
                with Container():
                    yield IgnoreTable(id="ignore_table")

            with TabPane("Log", id="log"):
                yield RichLog(highlight=True, markup=True, id="log_widget")

        yield tabbed_content
        yield Footer()

    def write_log(self, message: str, level: str = "info") -> None:
        """Log a message to the log widget"""
        log_widget = self.query_one("#log_widget", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "error":
            log_widget.write(
                f"[red]{timestamp}[/red] [bold red]ERROR[/bold red] {message}"
            )
        elif level == "warning":
            log_widget.write(
                f"[yellow]{timestamp}[/yellow] [bold yellow]WARN[/bold yellow] {message}"
            )
        elif level == "debug":
            log_widget.write(f"[dim]{timestamp} DEBUG {message}[/dim]")
        else:
            log_widget.write(
                f"[green]{timestamp}[/green] [bold green]INFO[/bold green] {message}"
            )

    def on_mount(self) -> None:
        """Initialize the data tables"""
        # Make sure log widget exists before trying to log
        try:
            self.write_log("Starting FilterBrowser...")
        except Exception:
            pass  # Log widget might not be ready yet

        # Set up files table
        files_table = self.query_one("#files_table", DataTable)
        terminal_width = self.size.width
        path_width = int(terminal_width * 0.7)
        sources_width = terminal_width - path_width - 3

        files_table.add_column("Path", width=path_width)
        files_table.add_column("Sources", width=sources_width)
        files_table.cursor_type = "row"
        files_table.zebra_stripes = True  # Make it more visible

        # Set up ignore table
        ignore_table = self.query_one("#ignore_table", DataTable)
        ignore_table.add_column("Ignore Pattern", width=terminal_width - 10)
        ignore_table.cursor_type = "row"
        ignore_table.zebra_stripes = True

        # Set up replace table
        replace_table = self.query_one("#replace_table", DataTable)
        replace_table.add_column("Find Pattern", width=int(terminal_width * 0.5))
        replace_table.add_column("Replace With", width=int(terminal_width * 0.5) - 10)
        replace_table.cursor_type = "row"
        replace_table.zebra_stripes = True

        # Write to log after tables are set up
        self.write_log("Starting FilterBrowser...")
        self.write_log(f"Files table initialized: {path_width}x{sources_width}")
        self.write_log("Ignore and replace tables initialized")

        # Load initial data
        self.load_files_data()
        self.load_filter_data()

        # Start checking for file changes
        self.set_interval(0.5, self.check_file_changes)
        self.write_log("File watching started")

    def check_file_changes(self) -> None:
        """Check for file changes"""
        for watch_file in self.watch_files:
            try:
                current_mtime = watch_file.stat().st_mtime
                if current_mtime > self.last_mtimes.get(watch_file, 0):
                    self.last_mtimes[watch_file] = current_mtime
                    if watch_file.name == "build_makefile.py":
                        self.write_log(f"Detected change in {watch_file.name}")
                        self.load_files_data()
                        self.notify("Reloaded build_makefile.py")
                    elif watch_file.name == "filters.json":
                        self.write_log(f"Detected change in {watch_file.name}")
                        self.load_filter_data()
                        self.notify("Reloaded filters.json")
            except Exception as e:
                self.write_log(f"Error checking {watch_file}: {e}", "error")

    def load_files_data(self) -> None:
        """Load file data using subprocess"""
        self.write_log("Loading files data...")
        table = self.query_one("#files_table", DataTable)

        # Auto-discover downloaders
        params_files = glob.glob(".cache/*.params")
        downloaders = [os.path.basename(f).replace(".params", "") for f in params_files]
        self.write_log(f"Found downloaders: {downloaders}", "debug")

        if not downloaders:
            self.write_log("No .params files found in .cache/", "warning")
            if not self.current_entries:
                table.clear()
                table.add_row("No .params files found in .cache/", "")
            return

        # Call build_makefile.py with --dump
        cmd = ["python3", "./scripts/build_makefile.py", "--dump"] + downloaders
        self.write_log(f"Running command: {' '.join(cmd)}", "debug")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.write_log(f"Command returned {len(result.stdout)} bytes", "debug")

            if result.stderr:
                self.write_log(f"Stderr: {result.stderr}", "warning")

            data = json.loads(result.stdout)
            targets = data['targets']
            filters_applied = data.get('filters_applied', 0)
            self.write_log(f"Parsed {len(targets)} targets from JSON ({filters_applied} filters applied)", "info")

        except subprocess.CalledProcessError as e:
            self.write_log(f"Error running build_makefile.py: {e}", "error")
            self.write_log(f"Return code: {e.returncode}", "error")
            if e.stderr:
                self.write_log(f"Stderr: {e.stderr}", "error")
            if e.stdout:
                self.write_log(f"Stdout: {e.stdout[:200]}...", "debug")

            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"Error running build_makefile.py: {e}", "")
            if e.stderr:
                table.add_row(e.stderr.strip(), "")
            return

        except json.JSONDecodeError as e:
            self.write_log(f"JSON decode error: {e}", "error")
            self.write_log(f"Raw output: {result.stdout[:200]}...", "debug")

            table.clear()
            self.current_entries.clear()
            self.sorted_keys.clear()
            table.add_row(f"JSON decode error: {e}", "")
            return

        # Terminal colors
        good_colors = [
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "bright_red",
            "bright_green",
            "bright_yellow",
            "bright_blue",
            "bright_magenta",
            "bright_cyan",
        ]

        # Build new entries
        new_entries = set()
        new_entry_details = {}

        self.write_log(f"Processing {len(targets)} target entries", "debug")

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

        self.write_log(f"Built {len(new_entries)} display entries", "info")

        # Simple update - just rebuild the table
        if new_entries != self.current_entries:
            self.write_log(
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

            self.write_log(f"Table updated with {table.row_count} rows", "info")
        else:
            self.write_log("No changes detected in entries", "debug")

    def load_filter_data(self) -> None:
        """Load filter configuration from filters.json"""
        self.write_log("Loading filter data...")
        
        ignore_table = self.query_one("#ignore_table", DataTable)
        replace_table = self.query_one("#replace_table", DataTable)
        
        ignore_table.clear()
        replace_table.clear()

        try:
            filter_data = load_filters()
            ignore_patterns = filter_data.get("files", {}).get("ignore", [])
            replace_patterns = filter_data.get("files", {}).get("replace", [])

            self.write_log(f"Loaded {len(ignore_patterns)} ignore patterns, {len(replace_patterns)} replace patterns", "info")

            # Load ignore patterns
            for pattern in ignore_patterns:
                ignore_table.add_row(pattern, key=pattern)

            # Load replace patterns
            for find_pattern, replace_with in replace_patterns:
                replace_table.add_row(find_pattern, replace_with, key=f"{find_pattern}|{replace_with}")

        except Exception as e:
            self.write_log(f"Error loading filter data: {e}", "error")
            ignore_table.add_row(f"Error loading filters: {e}", key="_error")
            replace_table.add_row(f"Error loading filters: {e}", "", key="_error")

    def action_ignore_filter(self) -> None:
        """Handle ignore filter action based on active tab"""
        tabbed_content = self.query_one(TabbedContent)

        if tabbed_content.active == "files":
            # Add ignore filter from selected file
            table = self.query_one("#files_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return

            try:
                row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
                if row_key:
                    safe_pattern = re.escape(str(row_key))
                    self.push_screen(
                        FilterEditModal(safe_pattern, "Add Ignore Pattern"),
                        self._add_ignore_callback,
                    )
            except Exception as e:
                self.write_log(f"Error getting row key: {e}", "error")

        elif tabbed_content.active == "ignore":
            # Delete selected ignore pattern
            table = self.query_one("#ignore_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return
            
            try:
                row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
                if row_key:
                    self._remove_ignore_pattern(str(row_key))
            except Exception as e:
                self.write_log(f"Error getting ignore pattern: {e}", "error")

        elif tabbed_content.active == "replace":
            # Delete selected replace pattern
            table = self.query_one("#replace_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return
            
            try:
                row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
                if row_key and "|" in row_key:
                    find_pattern, replace_with = row_key.split("|", 1)
                    self._remove_replace_pattern(find_pattern, replace_with)
            except Exception as e:
                self.write_log(f"Error getting replace pattern: {e}", "error")

    def action_replace_filter(self) -> None:
        """Handle replace filter action"""
        tabbed_content = self.query_one(TabbedContent)

        if tabbed_content.active == "files":
            # Add replace filter from selected file
            table = self.query_one("#files_table", DataTable)
            if table.row_count == 0 or table.cursor_row is None:
                return

            try:
                row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
                if row_key:
                    safe_pattern = re.escape(str(row_key))
                    self.push_screen(
                        ReplaceEditModal(safe_pattern, ""),
                        self._add_replace_callback,
                    )
            except Exception as e:
                self.write_log(f"Error getting row key: {e}", "error")

    def _add_ignore_callback(self, pattern: str) -> None:
        """Callback for adding an ignore pattern"""
        if not pattern:
            return

        try:
            filter_data = load_filters()
            ignore_patterns = filter_data.get("files", {}).get("ignore", [])

            if pattern not in ignore_patterns:
                ignore_patterns.append(pattern)
                filter_data["files"]["ignore"] = ignore_patterns
                save_filters(filter_data)

                self.notify(f"Added ignore pattern: {pattern}")
                self.load_filter_data()
                self.load_files_data()  # Reload files to apply filter
        except Exception as e:
            self.notify(f"Error adding ignore pattern: {e}", severity="error")

    def _add_replace_callback(self, result) -> None:
        """Callback for adding a replace pattern"""
        if not result or len(result) != 2:
            return

        find_pattern, replace_with = result
        if not find_pattern:
            return

        try:
            filter_data = load_filters()
            replace_patterns = filter_data.get("files", {}).get("replace", [])

            new_pattern = [find_pattern, replace_with]
            if new_pattern not in replace_patterns:
                replace_patterns.append(new_pattern)
                filter_data["files"]["replace"] = replace_patterns
                save_filters(filter_data)

                self.notify(f"Added replace pattern: {find_pattern} → {replace_with}")
                self.load_filter_data()
                self.load_files_data()  # Reload files to apply filter
        except Exception as e:
            self.notify(f"Error adding replace pattern: {e}", severity="error")

    def _remove_ignore_pattern(self, pattern: str) -> None:
        """Remove an ignore pattern"""
        try:
            filter_data = load_filters()
            ignore_patterns = filter_data.get("files", {}).get("ignore", [])

            if pattern in ignore_patterns:
                ignore_patterns.remove(pattern)
                filter_data["files"]["ignore"] = ignore_patterns
                save_filters(filter_data)

                self.notify(f"Removed ignore pattern: {pattern}")
                self.load_filter_data()
                self.load_files_data()  # Reload files to update
        except Exception as e:
            self.notify(f"Error removing ignore pattern: {e}", severity="error")

    def _remove_replace_pattern(self, find_pattern: str, replace_with: str) -> None:
        """Remove a replace pattern"""
        try:
            filter_data = load_filters()
            replace_patterns = filter_data.get("files", {}).get("replace", [])

            pattern_to_remove = [find_pattern, replace_with]
            if pattern_to_remove in replace_patterns:
                replace_patterns.remove(pattern_to_remove)
                filter_data["files"]["replace"] = replace_patterns
                save_filters(filter_data)

                self.notify(f"Removed replace pattern: {find_pattern} → {replace_with}")
                self.load_filter_data()
                self.load_files_data()  # Reload files to update
        except Exception as e:
            self.notify(f"Error removing replace pattern: {e}", severity="error")

    def action_delete_ignore_pattern(self) -> None:
        """Delete selected ignore pattern"""
        table = self.query_one("#ignore_table", IgnoreTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key:
                self._remove_ignore_pattern(str(row_key))
        except Exception as e:
            self.write_log(f"Error getting ignore pattern: {e}", "error")

    def action_edit_ignore_pattern(self) -> None:
        """Edit selected ignore pattern"""
        table = self.query_one("#ignore_table", IgnoreTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key:
                pattern = str(row_key)
                self.push_screen(
                    FilterEditModal(pattern, "Edit Ignore Pattern"),
                    lambda new_pattern: self._edit_ignore_pattern(pattern, new_pattern),
                )
        except Exception as e:
            self.write_log(f"Error getting ignore pattern: {e}", "error")

    def action_delete_replace_pattern(self) -> None:
        """Delete selected replace pattern"""
        table = self.query_one("#replace_table", ReplaceTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key and "|" in row_key:
                find_pattern, replace_with = row_key.split("|", 1)
                self._remove_replace_pattern(find_pattern, replace_with)
        except Exception as e:
            self.write_log(f"Error getting replace pattern: {e}", "error")

    def action_edit_replace_pattern(self) -> None:
        """Edit selected replace pattern"""
        table = self.query_one("#replace_table", ReplaceTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key and "|" in row_key:
                find_pattern, replace_with = row_key.split("|", 1)
                self.push_screen(
                    ReplaceEditModal(find_pattern, replace_with),
                    lambda result: self._edit_replace_pattern(find_pattern, replace_with, result),
                )
        except Exception as e:
            self.write_log(f"Error getting replace pattern: {e}", "error")

    def _edit_ignore_pattern(self, old_pattern: str, new_pattern: str) -> None:
        """Edit an ignore pattern"""
        if not new_pattern or old_pattern == new_pattern:
            return

        try:
            filter_data = load_filters()
            ignore_patterns = filter_data.get("files", {}).get("ignore", [])

            if old_pattern in ignore_patterns:
                idx = ignore_patterns.index(old_pattern)
                ignore_patterns[idx] = new_pattern
                filter_data["files"]["ignore"] = ignore_patterns
                save_filters(filter_data)

                self.notify(f"Updated ignore pattern: {old_pattern} → {new_pattern}")
                self.load_filter_data()
                self.load_files_data()
        except Exception as e:
            self.notify(f"Error editing ignore pattern: {e}", severity="error")

    def _edit_replace_pattern(self, old_find: str, old_replace: str, result) -> None:
        """Edit a replace pattern"""
        if not result or len(result) != 2:
            return

        new_find, new_replace = result
        if not new_find:
            return

        if old_find == new_find and old_replace == new_replace:
            return

        try:
            filter_data = load_filters()
            replace_patterns = filter_data.get("files", {}).get("replace", [])

            old_pattern = [old_find, old_replace]
            if old_pattern in replace_patterns:
                idx = replace_patterns.index(old_pattern)
                replace_patterns[idx] = [new_find, new_replace]
                filter_data["files"]["replace"] = replace_patterns
                save_filters(filter_data)

                self.notify(f"Updated replace pattern: {old_find}→{old_replace} to {new_find}→{new_replace}")
                self.load_filter_data()
                self.load_files_data()
        except Exception as e:
            self.notify(f"Error editing replace pattern: {e}", severity="error")

    def action_reload(self) -> None:
        """Manual reload"""
        self.load_files_data()
        self.load_filter_data()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


if __name__ == "__main__":
    app = FilterBrowser()
    app.run()

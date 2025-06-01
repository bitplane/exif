#!/usr/bin/env python3
"""
EXIF Sample Data Editor

A Textual-based application for managing filter configurations
and browsing sample data files.
"""

import re
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual.binding import Binding

from watch import FileWatcher
from log import LogWidget  
from images import ImagesWidget
from images.modals import IgnoreFilterModal, ReplaceFilterModal
from filters import load_filters, save_filters


class EditorApp(App):
    """EXIF Sample Data Editor Application"""

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

    def __init__(self):
        super().__init__()
        self.file_watcher = FileWatcher()
        self.log_widget = None
        self.images_widget = None

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(initial="images") as tabbed_content:
            with TabPane("Images", id="images"):
                self.images_widget = ImagesWidget(self)
                yield self.images_widget

            with TabPane("Log", id="log"):
                self.log_widget = LogWidget()
                yield self.log_widget

        yield tabbed_content
        yield Footer()

    def write_log(self, message: str, level: str = "info") -> None:
        """Log a message to the log widget"""
        if self.log_widget:
            self.log_widget.write_log(message, level)

    def on_mount(self) -> None:
        """Initialize the application"""
        self.write_log("Starting EXIF Sample Data Editor...")

        # Set up file watching
        build_makefile_path = Path(__file__).parent.parent / "build_makefile.py"
        filters_path = Path(__file__).parent.parent / "filters.json"
        
        self.file_watcher.watch_file(build_makefile_path, self._on_build_makefile_changed)
        self.file_watcher.watch_file(filters_path, self._on_filters_changed)

        # Set up tables
        terminal_width = self.size.width
        path_width, sources_width = self.images_widget.setup_tables(terminal_width)
        self.write_log(f"Tables initialized: {path_width}x{sources_width}")

        # Load initial data
        self.load_all_data()

        # Start file watching
        self.set_interval(0.5, self.file_watcher.check_changes)
        self.write_log("File watching started")

    def _on_build_makefile_changed(self, file_path: Path) -> None:
        """Handle build_makefile.py changes"""
        self.write_log(f"Detected change in {file_path.name}")
        self.images_widget.load_files_data(self.write_log)
        self.notify("Reloaded build_makefile.py")

    def _on_filters_changed(self, file_path: Path) -> None:
        """Handle filters.json changes"""
        self.write_log(f"Detected change in {file_path.name}")
        filter_data = load_filters()
        self.images_widget.load_filter_data(filter_data, self.write_log)
        self.notify("Reloaded filters.json")

    def load_all_data(self) -> None:
        """Load all data"""
        self.images_widget.load_files_data(self.write_log)
        filter_data = load_filters()
        self.images_widget.load_filter_data(filter_data, self.write_log)

    # Action methods called by table widgets
    def action_ignore_filter(self) -> None:
        """Handle ignore filter action"""
        active_tab = self.images_widget.get_active_tab()

        if active_tab == "files":
            # Add ignore filter from selected file
            selected_file = self.images_widget.get_selected_file()
            if selected_file:
                safe_pattern = re.escape(selected_file)
                self.push_screen(
                    IgnoreFilterModal(safe_pattern, "Add Ignore Pattern"),
                    self._add_ignore_callback,
                )

    def action_replace_filter(self) -> None:
        """Handle replace filter action"""
        active_tab = self.images_widget.get_active_tab()

        if active_tab == "files":
            # Add replace filter from selected file
            selected_file = self.images_widget.get_selected_file()
            if selected_file:
                safe_pattern = re.escape(selected_file)
                self.push_screen(
                    ReplaceFilterModal(safe_pattern, ""),
                    self._add_replace_callback,
                )

    def action_delete_ignore_pattern(self) -> None:
        """Delete selected ignore pattern"""
        pattern = self.images_widget.get_selected_ignore_pattern()
        if pattern:
            self._remove_ignore_pattern(pattern)

    def action_edit_ignore_pattern(self) -> None:
        """Edit selected ignore pattern"""
        pattern = self.images_widget.get_selected_ignore_pattern()
        if pattern:
            self.push_screen(
                IgnoreFilterModal(pattern, "Edit Ignore Pattern"),
                lambda new_pattern: self._edit_ignore_pattern(pattern, new_pattern),
            )

    def action_delete_replace_pattern(self) -> None:
        """Delete selected replace pattern"""
        pattern_tuple = self.images_widget.get_selected_replace_pattern()
        if pattern_tuple:
            find_pattern, replace_with = pattern_tuple
            self._remove_replace_pattern(find_pattern, replace_with)

    def action_edit_replace_pattern(self) -> None:
        """Edit selected replace pattern"""
        pattern_tuple = self.images_widget.get_selected_replace_pattern()
        if pattern_tuple:
            find_pattern, replace_with = pattern_tuple
            self.push_screen(
                ReplaceFilterModal(find_pattern, replace_with),
                lambda result: self._edit_replace_pattern(find_pattern, replace_with, result),
            )

    # Filter management callbacks
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
                self.load_all_data()
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
                self.load_all_data()
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
                self.load_all_data()
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
                self.load_all_data()
        except Exception as e:
            self.notify(f"Error removing replace pattern: {e}", severity="error")

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
                self.load_all_data()
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
                self.load_all_data()
        except Exception as e:
            self.notify(f"Error editing replace pattern: {e}", severity="error")

    def action_reload(self) -> None:
        """Manual reload"""
        self.load_all_data()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


if __name__ == "__main__":
    app = EditorApp()
    app.run()

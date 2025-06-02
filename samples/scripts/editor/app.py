#!/usr/bin/env python3
"""
EXIF Sample Data Editor

A Textual-based application for managing filter configurations
and browsing sample data files.
"""

import re
import json
import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane
from textual.binding import Binding

from files.watcher import FileWatcher
from files.filters import load, save, create_filter, FILTER_TYPES
from ui.log_tab import LogWidget, setup_logging
from ui.main import MainWidget
from ui.filters_modal import FilterModal, FilterListModal

# Setup module logger
logger = logging.getLogger("editor")


class EditorApp(App):
    """EXIF Sample Data Editor Application"""
    
    def on_exception(self, error: Exception) -> None:
        """Handle all uncaught exceptions"""
        logger.exception(f"Uncaught exception: {error}")
        self.notify(f"Error: {error}", severity="error")

    CSS = """
    /* Compact spacing */
    TabbedContent {
        padding: 0;
        margin: 0;
    }
    
    TabbedContent Tabs {
        padding: 0;
        margin: 0;
        height: 1;  /* Ultra compact */
    }
    
    TabbedContent Tab {
        padding: 0 1;  /* Minimal horizontal padding */
        margin: 0;
    }
    
    /* Style active tab when focused */
    TabbedContent:focus Tab.-active,
    TabbedContent Tabs:focus Tab.-active {
        text-style: bold reverse;
    }
    
    TabbedContent TabPane {
        padding: 0;
        margin: 0;
    }
    
    TabbedContent ContentSwitcher {
        padding: 0;
        margin: 0;
    }
    
    Container {
        padding: 0;
        margin: 0;
    }
    
    /* DataTable styling */
    DataTable {
        height: 100%;
        width: 100%;
        border: solid #444444;
        margin: 0;
        padding: 0;
    }
    DataTable > .datatable--header {
        text-style: bold;
    }
    
    /* Log styling */
    RichLog {
        border: solid #444444;
        margin: 0;
    }
    
    Header {
        margin: 0;
    }
    
    Footer {
        margin: 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f5", "reload", "Reload", show=True),
        Binding("ctrl+r", "reload", "Reload", show=False),
        Binding("ctrl+n", "new_filter", "New Filter", show=True),
        Binding("d", "delete_filter", "Delete Filter", show=False),
        Binding("i", "ignore_filter", "Ignore Filter", show=False),
        Binding("e", "edit_filter", "Edit Filter", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.file_watcher = FileWatcher()
        self.log_widget = None
        self.main_widget = None

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(initial="main") as tabbed_content:
            with TabPane("Main", id="main"):
                self.main_widget = MainWidget(self)
                yield self.main_widget

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
        # Setup logging with the log widget
        setup_logging(self.log_widget)
        
        logger.info("Starting EXIF Sample Data Editor...")

        # Set up tables
        terminal_width = self.size.width
        path_width, sources_width = self.main_widget.setup_tables(terminal_width)
        logger.info(f"Tables initialized: {path_width}x{sources_width}")

        # Load initial data
        self.load_all_data()

    def load_all_data(self) -> None:
        """Load all data"""
        self.main_widget.load_files_data()
        
        # Load filters from disk
        filters_path = Path(__file__).parent.parent / "filters.json"
        try:
            with open(filters_path, "r") as f:
                filter_data = json.load(f)
                logger.debug(f"Loaded filter data: {filter_data}")
        except Exception as e:
            logger.error(f"Error loading filters.json: {e}")
            filter_data = {"files": {"ignore": [], "edit": []}}
        
        self.main_widget.load_filter_data(filter_data)
    
    def _save_filters(self, filter_objects):
        """Save filters to disk"""
        filters_path = Path(__file__).parent.parent / "filters.json"
        filter_data = save(filter_objects)
        
        temp_file = filters_path.with_suffix(".json.tmp")
        with open(temp_file, "w") as f:
            json.dump(filter_data, f, indent=2)
        temp_file.rename(filters_path)

    # Action methods called by table widgets
    def action_ignore_filter(self) -> None:
        """Handle ignore filter action"""
        active_tab = self.main_widget.get_active_tab()

        if active_tab == "files":
            # Add ignore filter from selected file using generic modal
            selected_file = self.main_widget.get_selected_file()
            if selected_file:
                safe_pattern = re.escape(selected_file)
                self.push_screen(
                    FilterModal(
                        "ignore", 
                        "Add Ignore Filter",
                        {"pattern": safe_pattern}
                    ),
                    lambda values: self._add_filter_simple("ignore", values),
                )

    def action_edit_filter(self) -> None:
        """Handle edit filter action (from 'e' key)"""
        active_tab = self.main_widget.get_active_tab()

        if active_tab == "files":
            # Add edit filter from selected file using generic modal
            selected_file = self.main_widget.get_selected_file()
            if selected_file:
                safe_pattern = re.escape(selected_file)
                self.push_screen(
                    FilterModal(
                        "edit",
                        "Add Edit Filter",
                        {"find": safe_pattern, "replacement": ""}
                    ),
                    lambda values: self._add_filter_simple("edit", values),
                )

    def action_delete_filter(self) -> None:
        """Delete selected filter"""
        filter_obj, index = self.main_widget.get_selected_filter()
        if filter_obj is not None:
            self._remove_filter_at_index(index)

    def action_edit_filter(self) -> None:
        """Edit selected filter"""
        filter_obj, index = self.main_widget.get_selected_filter()
        if filter_obj is not None:
            # Get filter type dynamically
            filter_type = None
            initial_values = {}
            
            # Find which type this filter is
            for fname, fclass in FILTER_TYPES.items():
                if isinstance(filter_obj, fclass):
                    filter_type = fname
                    # Get current values for each parameter
                    for param_name, _, _ in fclass.PARAMETERS:
                        if hasattr(filter_obj, param_name):
                            initial_values[param_name] = getattr(filter_obj, param_name)
                    break
            
            if filter_type:
                self.push_screen(
                    FilterModal(filter_type, f"Edit {filter_type.title()} Filter", initial_values),
                    lambda values: self._edit_filter_at_index(index, filter_type, values),
                )

    # Filter management callbacks
    def _add_filter_simple(self, filter_type: str, values: dict) -> None:
        """Simple callback for adding a filter by type"""
        if not values:
            return

        try:
            logger.debug(f"Adding {filter_type} filter with values: {values}")
            
            filter_class = FILTER_TYPES.get(filter_type)
            if not filter_class:
                logger.warning(f"Unknown filter type: {filter_type}")
                return
            
            # Create filter with parameter values in order
            param_values = [values.get(p[0]) for p in filter_class.PARAMETERS]
            new_filter = create_filter(filter_type, *param_values)
            logger.info(f"Created {filter_type} filter: {new_filter}")
            
            # Add through the filters widget
            filters_widget = self.main_widget.get_filters_widget()
            filters_widget.add_filter(new_filter)
            
            # Save to disk
            self._save_filters(filters_widget.filter_objects)
            self.notify(f"Added {new_filter}")
            
        except Exception as e:
            logger.exception(f"Error adding filter: {e}")
            self.notify(f"Error adding filter: {e}", severity="error")

    def _remove_filter_at_index(self, index: int) -> None:
        """Remove a filter by index"""
        try:
            filters_widget = self.main_widget.get_filters_widget()
            removed = filters_widget.remove_filter_at(index)
            if removed:
                self._save_filters(filters_widget.filter_objects)
                self.notify(f"Removed {removed}")
        except Exception as e:
            self.notify(f"Error removing filter: {e}", severity="error")

    def _edit_filter_at_index(self, index: int, filter_type: str, values: dict) -> None:
        """Edit a filter at index"""
        if not values:
            return
            
        filters_widget = self.main_widget.get_filters_widget()
        
        # Create new filter object
        filter_class = FILTER_TYPES.get(filter_type)
        if not filter_class:
            logger.error(f"Unknown filter type: {filter_type}")
            return
        
        # Create filter with parameter values
        param_values = [values.get(p[0]) for p in filter_class.PARAMETERS]
        new_filter = create_filter(filter_type, *param_values)
        
        # Check if filter actually changed
        old_filter = filters_widget.filter_objects[index] if index < len(filters_widget.filter_objects) else None
        if old_filter and old_filter.to_dict() == new_filter.to_dict():
            logger.debug("Filter unchanged, skipping update")
            self.notify("Filter unchanged")
            return
        
        # Update in widget
        if filters_widget.update_filter_at(index, new_filter):
            self._save_filters(filters_widget.filter_objects)
            self.notify(f"Updated filter: {new_filter}")

    def action_reload(self) -> None:
        """Manual reload"""
        self.load_all_data()

    def action_new_filter(self) -> None:
        """Show filter type selection modal"""
        def handle_filter_type(filter_type):
            if filter_type:
                self.push_screen(
                    FilterModal(filter_type, f"Add {filter_type.title()} Filter"),
                    lambda values: self._add_filter_simple(filter_type, values)
                )
        
        self.push_screen(FilterListModal(), handle_filter_type)

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


if __name__ == "__main__":
    app = EditorApp()
    app.run()

"""
Unified filters table widget
"""

import hashlib
import logging
from textual.widgets import DataTable
from textual.binding import Binding

logger = logging.getLogger("editor")


class FiltersTable(DataTable):
    """Filters table with specific bindings"""
    
    BINDINGS = [
        Binding("delete", "delete_filter", "Delete", show=True),
        Binding("enter", "edit_filter", "Edit", show=True),
        Binding("insert", "add_filter", "Add", show=True),
    ]
    
    def action_delete_filter(self):
        self.app.action_delete_filter()
    
    def action_edit_filter(self):
        self.app.action_edit_filter()
    
    def action_add_filter(self):
        self.app.action_new_filter()


class FiltersTabWidget:
    """Widget for managing all filters in a unified view"""
    
    def __init__(self, editor_app):
        self.editor_app = editor_app
        self.filter_objects = []
        self.on_filters_changed = None  # Callback when filters change
        self._table = None  # Reference to the table for updates
    
    def setup_table(self, table: FiltersTable, terminal_width: int):
        """Initialize the filters table"""
        table.add_column("Type", width=15)
        table.add_column("Filter", width=terminal_width - 25)
        table.cursor_type = "row"
        table.zebra_stripes = True
    
    def load_data(self, table: FiltersTable, filters: list):
        """Load filters into the table"""
        self._table = table  # Store reference for updates
        table.clear()
        self.filter_objects = filters
        
        # Terminal colors for filter types
        colors = [
            "red", "green", "yellow", "blue", "magenta", "cyan",
            "bright_red", "bright_green", "bright_yellow", 
            "bright_blue", "bright_magenta", "bright_cyan",
        ]
        
        for i, filter_obj in enumerate(filters):
            # Get filter type name from class
            filter_type = filter_obj.__class__.__name__.replace("Filter", "").lower()
            
            # Color based on filter type (deterministic)
            hash_value = int(hashlib.md5(filter_type.encode()).hexdigest()[:8], 16)
            color_index = hash_value % len(colors)
            color = colors[color_index]
            
            # Colored type column
            colored_type = f"[{color}]{filter_type}[/]"
            
            # Escape Rich markup in filter description
            filter_desc = str(filter_obj).replace("[", "\\[").replace("]", "\\]")
            
            table.add_row(colored_type, filter_desc, key=i)
        
        logger.debug(f"Loaded {len(filters)} filters")
    
    def get_selected_filter_info(self, table: FiltersTable):
        """Get the currently selected filter object and index"""
        if table.row_count == 0 or table.cursor_row is None:
            return None, None
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key is not None and 0 <= row_key < len(self.filter_objects):
                return self.filter_objects[row_key], row_key
            return None, None
        except Exception:
            return None, None
    
    def set_filters(self, filters: list):
        """Set the filter list and notify listeners"""
        self.filter_objects = filters
        if self.on_filters_changed:
            self.on_filters_changed(filters)
    
    def add_filter(self, filter_obj):
        """Add a filter and notify listeners"""
        self.filter_objects.append(filter_obj)
        self._refresh_table()
        if self.on_filters_changed:
            self.on_filters_changed(self.filter_objects)
    
    def remove_filter_at(self, index: int):
        """Remove filter at index and notify listeners"""
        if 0 <= index < len(self.filter_objects):
            removed = self.filter_objects.pop(index)
            self._refresh_table()
            if self.on_filters_changed:
                self.on_filters_changed(self.filter_objects)
            return removed
        return None
    
    def update_filter_at(self, index: int, new_filter):
        """Update filter at index and notify listeners"""
        if 0 <= index < len(self.filter_objects):
            self.filter_objects[index] = new_filter
            self._refresh_table()
            if self.on_filters_changed:
                self.on_filters_changed(self.filter_objects)
            return True
        return False
    
    def _refresh_table(self):
        """Refresh the filters table display"""
        if self._table:
            self.load_data(self._table, self.filter_objects)
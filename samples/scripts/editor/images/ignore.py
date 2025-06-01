"""
Ignore patterns table widget
"""

from textual.widgets import DataTable
from textual.binding import Binding


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


class IgnoreWidget:
    """Widget for managing ignore patterns"""
    
    def __init__(self, editor_app):
        self.editor_app = editor_app
    
    def setup_table(self, table: IgnoreTable, terminal_width: int):
        """Initialize the ignore patterns table"""
        table.add_column("Ignore Pattern", width=terminal_width - 10)
        table.cursor_type = "row"
        table.zebra_stripes = True
    
    def load_data(self, table: IgnoreTable, ignore_patterns: list, log_writer):
        """Load ignore patterns into the table"""
        table.clear()
        
        for pattern in ignore_patterns:
            table.add_row(pattern, key=pattern)
        
        log_writer(f"Loaded {len(ignore_patterns)} ignore patterns", "debug")
    
    def get_selected_pattern(self, table: IgnoreTable):
        """Get the currently selected pattern"""
        if table.row_count == 0 or table.cursor_row is None:
            return None
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            return str(row_key) if row_key else None
        except Exception:
            return None
"""
Replace patterns table widget
"""

from textual.widgets import DataTable
from textual.binding import Binding


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


class ReplaceWidget:
    """Widget for managing replace patterns"""
    
    def __init__(self, editor_app):
        self.editor_app = editor_app
    
    def setup_table(self, table: ReplaceTable, terminal_width: int):
        """Initialize the replace patterns table"""
        table.add_column("Find Pattern", width=int(terminal_width * 0.5))
        table.add_column("Replace With", width=int(terminal_width * 0.5) - 10)
        table.cursor_type = "row"
        table.zebra_stripes = True
    
    def load_data(self, table: ReplaceTable, replace_patterns: list, log_writer):
        """Load replace patterns into the table"""
        table.clear()
        
        for find_pattern, replace_with in replace_patterns:
            table.add_row(find_pattern, replace_with, key=f"{find_pattern}|{replace_with}")
        
        log_writer(f"Loaded {len(replace_patterns)} replace patterns", "debug")
    
    def get_selected_pattern(self, table: ReplaceTable):
        """Get the currently selected pattern as (find, replace) tuple"""
        if table.row_count == 0 or table.cursor_row is None:
            return None
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            if row_key and "|" in row_key:
                find_pattern, replace_with = row_key.split("|", 1)
                return (find_pattern, replace_with)
            return None
        except Exception:
            return None
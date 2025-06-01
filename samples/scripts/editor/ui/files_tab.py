"""
Files table widget
"""

import hashlib
import time
import logging
from textual.widgets import DataTable
from textual.binding import Binding
from .table import VirtualDataTable
from files.file_list import FileList

logger = logging.getLogger("editor")


class FilesTable(VirtualDataTable):
    """Files table with specific bindings"""
    
    BINDINGS = [
        Binding("delete", "ignore_filter", "Ignore", show=True),
        Binding("f2", "edit_filter", "Edit", show=True),
    ]
    
    def action_ignore_filter(self):
        self.app.action_ignore_filter()
    
    def action_edit_filter(self):
        self.app.action_edit_filter()


class FilesWidget:
    """Widget for managing the files display"""
    
    def __init__(self, editor_app):
        self.editor_app = editor_app
        self.file_list = FileList()
    
    def setup_table(self, table: FilesTable, terminal_width: int):
        """Initialize the files table"""
        path_width = int(terminal_width * 0.7)
        sources_width = terminal_width - path_width - 3
        
        table.add_column("Path", width=path_width)
        table.add_column("Sources", width=sources_width)
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        return path_width, sources_width
    
    def load_data(self, table: FilesTable):
        """Load file data and setup table"""
        logger.info("Loading files data...")
        
        try:
            # Load and refresh data
            self.file_list.load()
            logger.debug(f"Loaded {self.file_list.get_file_count()} raw files")
            
            downloaders = self.file_list.get_downloaders()
            if not downloaders:
                logger.warning("No .params files found in .cache/")
                table.clear()
                table.add_row("No .params files found in .cache/", "")
                return
            
            logger.debug(f"Found downloaders: {downloaders}")
            
            # Refresh display with current filters
            self.refresh_display(table)
            
        except Exception as e:
            logger.error(f"Error loading file data: {e}")
            table.clear()
            table.add_row(f"Error loading file data: {e}", "")
    
    def refresh_display(self, table: FilesTable):
        """Refresh the table display without reloading from disk"""
        start_time = time.time()
        
        # FileList handles filtering internally
        self.file_list.refresh()
        
        # Terminal colors
        good_colors = [
            "red", "green", "yellow", "blue", "magenta", "cyan",
            "bright_red", "bright_green", "bright_yellow", 
            "bright_blue", "bright_magenta", "bright_cyan",
        ]
        
        # Build display data with colors
        virtual_data = []
        for i in range(len(self.file_list)):
            key, path, sources_str = self.file_list[i]
            
            # Color based on first source
            primary_source = sources_str.split(", ")[0] if sources_str else "unknown"
            hash_value = int(hashlib.md5(primary_source.encode()).hexdigest()[:8], 16)
            color_index = hash_value % len(good_colors)
            source_color = good_colors[color_index]
            
            colored_sources = f"[{source_color}]{sources_str}[/]"
            virtual_data.append((key, path, colored_sources))
        
        # Update table
        table.set_virtual_data(virtual_data)
        
        elapsed = time.time() - start_time
        logger.info(f"Display refreshed: {len(virtual_data)} files in {elapsed:.3f}s")
    
    def get_selected_file(self, table: FilesTable):
        """Get the currently selected file path"""
        if table.row_count == 0 or table.cursor_row is None:
            return None
        
        try:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
            return str(row_key) if row_key else None
        except Exception:
            return None
    
    def set_filters(self, filters):
        """Set the filter list"""
        self.file_list.set_filters(filters)
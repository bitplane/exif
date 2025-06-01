"""
Main widget containing files and filters tabs
"""

import logging
from textual.widgets import TabbedContent, TabPane
from textual.containers import Container
from .files_tab import FilesTable, FilesWidget  
from .filters_tab import FiltersTable, FiltersTabWidget
from files.filters import load

logger = logging.getLogger("editor")


class MainWidget(Container):
    """Container for the images management interface"""
    
    def __init__(self, editor_app):
        super().__init__()
        self.editor_app = editor_app
        self.files_widget = FilesWidget(editor_app)
        self.filters_widget = FiltersTabWidget(editor_app)
        
        # Wire up the callback to push filter changes to files widget
        self.filters_widget.on_filters_changed = self._on_filters_changed
    
    def _on_filters_changed(self, filters):
        """Called when filters change in the filters tab"""
        # Update the files widget with new filters
        self.files_widget.set_filters(filters)
        # Refresh the display with new filters (no disk reload)
        files_table = self.query_one("#files_table", FilesTable)
        self.files_widget.refresh_display(files_table)
    
    def compose(self):
        with TabbedContent(initial="files") as tabbed_content:
            with TabPane("Files", id="files"):
                with Container():
                    yield FilesTable(id="files_table")
            
            with TabPane("Filters", id="filters"):
                with Container():
                    yield FiltersTable(id="filters_table")
    
    def setup_tables(self, terminal_width: int):
        """Initialize all tables"""
        files_table = self.query_one("#files_table", FilesTable)
        filters_table = self.query_one("#filters_table", FiltersTable)
        
        # Setup each table
        path_width, sources_width = self.files_widget.setup_table(files_table, terminal_width)
        self.filters_widget.setup_table(filters_table, terminal_width)
        
        return path_width, sources_width
    
    def load_files_data(self):
        """Load files data"""
        files_table = self.query_one("#files_table", FilesTable)
        self.files_widget.load_data(files_table)
    
    def load_filter_data(self, filter_data: dict):
        """Load filter data"""
        logger.debug(f"load_filter_data called with: {filter_data}")
        
        # Convert JSON to Filter objects
        filters = load(filter_data)
        logger.debug(f"Converted to {len(filters)} filter objects")
        
        # Set filters on files widget
        self.files_widget.set_filters(filters)
        
        # Load filters into the filters table
        filters_table = self.query_one("#filters_table", FiltersTable)
        self.filters_widget.load_data(filters_table, filters)
        
        logger.info(f"Loaded {len(filters)} filters")
    
    def get_selected_file(self):
        """Get selected file from files table"""
        files_table = self.query_one("#files_table", FilesTable)
        return self.files_widget.get_selected_file(files_table)
    
    def get_selected_filter(self):
        """Get selected filter object and index"""
        filters_table = self.query_one("#filters_table", FiltersTable)
        return self.filters_widget.get_selected_filter_info(filters_table)
    
    def get_filters_widget(self):
        """Get the filters widget for direct manipulation"""
        return self.filters_widget
    
    def get_active_tab(self):
        """Get the currently active tab"""
        tabbed_content = self.query_one(TabbedContent)
        return tabbed_content.active
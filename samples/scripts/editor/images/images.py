"""
Images management widget with nested tabs
"""

from textual.widgets import TabbedContent, TabPane
from textual.containers import Container
from .files import FilesTable, FilesWidget  
from .replace import ReplaceTable, ReplaceWidget
from .ignore import IgnoreTable, IgnoreWidget


class ImagesWidget(Container):
    """Container for the images management interface"""
    
    def __init__(self, editor_app):
        super().__init__()
        self.editor_app = editor_app
        self.files_widget = FilesWidget(editor_app)
        self.replace_widget = ReplaceWidget(editor_app) 
        self.ignore_widget = IgnoreWidget(editor_app)
    
    def compose(self):
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
    
    def setup_tables(self, terminal_width: int):
        """Initialize all tables"""
        files_table = self.query_one("#files_table", FilesTable)
        replace_table = self.query_one("#replace_table", ReplaceTable)
        ignore_table = self.query_one("#ignore_table", IgnoreTable)
        
        # Setup each table
        path_width, sources_width = self.files_widget.setup_table(files_table, terminal_width)
        self.replace_widget.setup_table(replace_table, terminal_width)
        self.ignore_widget.setup_table(ignore_table, terminal_width)
        
        return path_width, sources_width
    
    def load_files_data(self, log_writer):
        """Load files data"""
        files_table = self.query_one("#files_table", FilesTable)
        self.files_widget.load_data(files_table, log_writer)
    
    def load_filter_data(self, filter_data: dict, log_writer):
        """Load filter data"""
        ignore_patterns = filter_data.get("files", {}).get("ignore", [])
        replace_patterns = filter_data.get("files", {}).get("replace", [])
        
        ignore_table = self.query_one("#ignore_table", IgnoreTable)
        replace_table = self.query_one("#replace_table", ReplaceTable)
        
        self.ignore_widget.load_data(ignore_table, ignore_patterns, log_writer)
        self.replace_widget.load_data(replace_table, replace_patterns, log_writer)
        
        log_writer(f"Loaded {len(ignore_patterns)} ignore patterns, {len(replace_patterns)} replace patterns", "info")
    
    def get_selected_file(self):
        """Get selected file from files table"""
        files_table = self.query_one("#files_table", FilesTable)
        return self.files_widget.get_selected_file(files_table)
    
    def get_selected_ignore_pattern(self):
        """Get selected ignore pattern"""
        ignore_table = self.query_one("#ignore_table", IgnoreTable)
        return self.ignore_widget.get_selected_pattern(ignore_table)
    
    def get_selected_replace_pattern(self):
        """Get selected replace pattern"""
        replace_table = self.query_one("#replace_table", ReplaceTable)
        return self.replace_widget.get_selected_pattern(replace_table)
    
    def get_active_tab(self):
        """Get the currently active tab"""
        tabbed_content = self.query_one(TabbedContent)
        return tabbed_content.active
"""
Virtual DataTable for handling large datasets efficiently
"""

import logging
from textual.widgets import DataTable
from typing import Tuple
from textual.coordinate import Coordinate

logger = logging.getLogger("editor")


class VirtualDataTable(DataTable):
    """DataTable with virtual data that loads on-demand"""
    
    def __init__(self, data_provider, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Data provider is mandatory
        self.data_provider = data_provider
        # Track loaded row versions: {row_index: version}
        self.row_versions = {}
    
    def _adjust_row_count(self):
        """Adjust table rows to match data provider size"""
        provider_size = len(self.data_provider)
        current_size = self.row_count
        
        # Add rows
        empty_row = [""] * len(self.columns)
        for i in range(current_size, provider_size):
            self.add_row(*empty_row, key=str(i))
        
        # Remove rows from the end
        for i in range(provider_size, current_size):
            self.remove_row(str(i))
    
    def update_range(self, start: int, stop: int):
        """Update a range of rows from the data provider"""
        current_version = self.data_provider.get_version()
        logger.debug(f"Updating range: {start} to {stop}")
        
        # Update rows that need it
        start = max(start, 0)
        stop = min(stop, len(self.data_provider))
        for row_idx in range(start, stop):
            if self.row_versions.get(row_idx, -1) != current_version:
                row_data = self.data_provider.format_row(row_idx)
                for col_idx, value in enumerate(row_data):
                    self.update_cell_at(Coordinate(row_idx, col_idx), value)
                self.row_versions[row_idx] = current_version
        
    def _get_offsets(self, y: int) -> tuple:
        """Override to lazy-load visible rows before rendering"""
        # Get the result first so we know where we are
        result = super()._get_offsets(y)
        
        # Adjust row count to match provider
        self._adjust_row_count()
        
        # Calculate visible range
        # y is the position from top of table in screen space
        row_height = 1  # Each row is 1 line high in DataTable
        
        # Get scroll position to find what's at the top of the viewport
        scroll_y = self.scroll_offset.y
        
        # Calculate the row at position y
        current_row = (y + scroll_y) // row_height
        
        # Get viewport height to determine range
        viewport_height = self.size.height
        if self.show_header:
            viewport_height -= self.header_height
        
        # Calculate visible range with some buffer
        buffer = 5
        first_visible = max(0, current_row - viewport_height // 2 - buffer)
        last_visible = min(len(self.data_provider), current_row + viewport_height // 2 + buffer)
        
        # Update the visible range
        self.update_range(first_visible, last_visible)
        
        return result

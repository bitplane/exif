"""
Virtual DataTable for handling large datasets efficiently
"""

from textual.widgets import DataTable
from typing import Dict, List, Tuple, Any, Union
from textual.coordinate import Coordinate


class VirtualDataTable(DataTable):
    """DataTable with virtual data that loads on-demand"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Our virtual data store: list of (key, col1, col2, ...)
        self.virtual_data: List[Tuple[str, ...]] = []
        
    def set_virtual_data(self, data: List[Tuple[str, ...]]):
        """Set the virtual dataset - doesn't actually populate the table"""
        self.virtual_data = data
        
        # Clear and add placeholder rows for proper scrolling
        self.clear(columns=False)
        
        # Add minimal placeholder rows - just enough for DataTable to know the size
        for i, row_data in enumerate(data):
            key = row_data[0]
            # Add completely empty row - we'll populate on access
            placeholder_row = [""] * (len(row_data) - 1) 
            self.add_row(*placeholder_row, key=key)
    
    def get_row_at(self, row_index: int):
        """Override to return virtual data on access"""
        # If we have virtual data for this row, return it
        if 0 <= row_index < len(self.virtual_data):
            virtual_row = self.virtual_data[row_index]
            
            # Update the actual DataTable row if needed
            self._ensure_row_loaded(row_index)
            
        # Return the actual DataTable row
        return super().get_row_at(row_index)
    
    def get_cell_at(self, coordinate: Coordinate):
        """Override to return virtual data on access"""
        row_index = coordinate.row
        
        # Ensure the row is loaded
        if 0 <= row_index < len(self.virtual_data):
            self._ensure_row_loaded(row_index)
            
        return super().get_cell_at(coordinate)
    
    def _ensure_row_loaded(self, row_index: int):
        """Load virtual data into the actual DataTable row if not already loaded"""
        if row_index >= len(self.virtual_data):
            return
            
        virtual_row = self.virtual_data[row_index]
        display_data = virtual_row[1:]  # Skip key, just get display columns
        
        # Check if row needs updating (simple check: is first cell empty?)
        try:
            current_cell = super().get_cell_at(Coordinate(row_index, 0))
            if current_cell == "":  # Placeholder, needs loading
                # Update all cells in this row
                for col_idx, value in enumerate(display_data):
                    self.update_cell_at(Coordinate(row_index, col_idx), value)
        except Exception:
            pass  # Don't crash on access errors
    
    def add_virtual_row(self, data: Tuple[str, ...]):
        """Add a row to virtual data"""
        self.virtual_data.append(data)
        
        # Add placeholder to actual table
        key = data[0]
        placeholder_row = [""] * (len(data) - 1)
        self.add_row(*placeholder_row, key=key)
    
    def update_virtual_row(self, index: int, data: Tuple[str, ...]):
        """Update a row in virtual data"""
        if 0 <= index < len(self.virtual_data):
            self.virtual_data[index] = data
            
            # Clear the actual row so it gets reloaded
            display_data = [""] * (len(data) - 1)
            for col_idx, _ in enumerate(display_data):
                try:
                    self.update_cell_at(Coordinate(index, col_idx), "")
                except Exception:
                    pass
    
    def remove_virtual_row(self, index: int):
        """Remove a row from virtual data"""
        if 0 <= index < len(self.virtual_data):
            # Remove from virtual data
            del self.virtual_data[index]
            
            # Remove from actual table
            try:
                row = super().get_row_at(index)
                self.remove_row(row.key)
            except Exception:
                pass
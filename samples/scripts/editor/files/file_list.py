"""
File list management - loads and caches file data from params files
"""

import os
import glob
import logging
import time
from typing import List, Dict, Tuple, Optional, Set, TYPE_CHECKING, Any
from collections import OrderedDict

logger = logging.getLogger("editor")


class FileList:
    """Single data source for file lists - loads from params, applies filters, serves table data"""
    
    def __init__(self, filters=None):
        self._raw_data: OrderedDict[str, List[Tuple[str, str, str]]] = OrderedDict()
        self._downloaders: List[str] = []
        self._is_loaded = False
        self.filters = filters or []
        
        # Cached filtered data for table display
        self._filtered_data: List[Tuple[str, str, str]] = []  # (key, path, sources)
        self._needs_refresh = True
    
    def load(self) -> None:
        """Load all file data from .params files"""
        # Auto-discover downloaders
        params_files = glob.glob(".cache/*.params")
        self._downloaders = [os.path.basename(f).replace(".params", "") for f in params_files]
        
        # Reset data
        self._raw_data.clear()
        
        # Load each params file
        for downloader in self._downloaders:
            self._load_params_file(downloader)
        
        self._is_loaded = True
    
    def _load_params_file(self, downloader: str) -> None:
        """Load a single params file"""
        params_file = f".cache/{downloader}.params"
        
        if not os.path.exists(params_file):
            return
        
        with open(params_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Split into filename and args
                parts = line.split(' ', 1)
                if len(parts) < 2:
                    continue
                
                filename, args = parts
                target = f"data/{filename}"
                
                # Extract the path part after "data/"
                path = target[5:] if target.startswith("data/") else target
                
                # Store raw data: (path, source, command_args)
                if path not in self._raw_data:
                    self._raw_data[path] = []
                
                self._raw_data[path].append((path, downloader, args))
    
    def apply_filters(self, filters: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Apply filters to the file list and return filtered results
        
        Returns dict mapping filtered paths to their sources with applied filters info
        """
        if not self._is_loaded:
            self.load()
        
        start_time = time.time()
        results = OrderedDict()
        
        for original_path, sources in self._raw_data.items():
            # Apply filters to get final path
            current_path = original_path
            applied_filters = []
            
            try:
                for filter_obj in filters:
                    old_path = current_path
                    current_path = filter_obj.apply(current_path)
                    if current_path != old_path:
                        applied_filters.append({
                            "type": str(filter_obj),
                            "from": old_path,
                            "to": current_path
                        })
            except StopIteration:
                # File filtered out
                continue
            
            # If path survived filtering, add to results
            if current_path not in results:
                results[current_path] = []
            
            # Add all sources for this path
            for path, source, args in sources:
                results[current_path].append({
                    "original_path": original_path,
                    "source": source,
                    "args": args,
                    "applied_filters": applied_filters.copy()
                })
        
        elapsed = time.time() - start_time
        logger.debug(f"Filter execution completed: {len(self._raw_data)} → {len(results)} files in {elapsed:.3f}s")
        return results
    
    def get_raw_files(self) -> List[str]:
        """Get all raw file paths (unfiltered)"""
        if not self._is_loaded:
            self.load()
        return list(self._raw_data.keys())
    
    def get_downloaders(self) -> List[str]:
        """Get list of discovered downloaders"""
        if not self._is_loaded:
            self.load()
        return self._downloaders.copy()
    
    def get_file_count(self) -> int:
        """Get count of raw files"""
        return len(self._raw_data)
    
    def get_source_info(self, path: str) -> List[Tuple[str, str]]:
        """Get source info for a specific path
        Returns list of (source, args) tuples
        """
        if path not in self._raw_data:
            return []
        return [(source, args) for _, source, args in self._raw_data[path]]
    
    def set_filters(self, filters):
        """Update filters and mark for refresh"""
        self.filters = filters
        self._needs_refresh = True
    
    def refresh(self):
        """Refresh filtered data for table display"""
        if not self._is_loaded:
            self.load()
        
        # Apply filters and build display data
        filtered = self.apply_filters(self.filters)
        self._filtered_data = []
        
        for path, sources in sorted(filtered.items()):
            source_names = [s["source"] for s in sources]
            sources_str = ", ".join(source_names)
            self._filtered_data.append((path, path, sources_str))
        
        self._needs_refresh = False
    
    # Table interface methods
    def __len__(self):
        """Number of filtered items for table display"""
        if self._needs_refresh:
            self.refresh()
        return len(self._filtered_data)
    
    def __getitem__(self, index):
        """Get item for table display: (key, path, sources)"""
        if self._needs_refresh:
            self.refresh()
        if 0 <= index < len(self._filtered_data):
            return self._filtered_data[index]
        raise IndexError(f"Index {index} out of range")
    
    def get_keys(self):
        """Get all keys (paths) for quick lookup"""
        if self._needs_refresh:
            self.refresh()
        return [item[0] for item in self._filtered_data]

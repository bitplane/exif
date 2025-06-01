"""
File watching module with callback support
"""

import os
from pathlib import Path
from typing import Dict, List, Callable
from textual.app import App


class FileWatcher:
    """File watcher that triggers callbacks when files change"""
    
    def __init__(self):
        self.watched_files: Dict[Path, List[Callable]] = {}
        self.last_mtimes: Dict[Path, float] = {}
    
    def watch_file(self, file_path: Path, callback: Callable) -> None:
        """Add a callback for when a file changes"""
        if file_path not in self.watched_files:
            self.watched_files[file_path] = []
        self.watched_files[file_path].append(callback)
        
        # Initialize mtime
        if file_path not in self.last_mtimes:
            self.last_mtimes[file_path] = 0
    
    def unwatch_file(self, file_path: Path, callback: Callable = None) -> None:
        """Remove callback(s) for a file"""
        if file_path not in self.watched_files:
            return
            
        if callback is None:
            # Remove all callbacks for this file
            del self.watched_files[file_path]
            if file_path in self.last_mtimes:
                del self.last_mtimes[file_path]
        else:
            # Remove specific callback
            if callback in self.watched_files[file_path]:
                self.watched_files[file_path].remove(callback)
            
            # If no callbacks left, remove the file entirely
            if not self.watched_files[file_path]:
                del self.watched_files[file_path]
                if file_path in self.last_mtimes:
                    del self.last_mtimes[file_path]
    
    def check_changes(self) -> None:
        """Check all watched files for changes and trigger callbacks"""
        for file_path, callbacks in self.watched_files.items():
            try:
                if not file_path.exists():
                    continue
                    
                current_mtime = file_path.stat().st_mtime
                if current_mtime > self.last_mtimes.get(file_path, 0):
                    self.last_mtimes[file_path] = current_mtime
                    
                    # Trigger all callbacks for this file
                    for callback in callbacks:
                        try:
                            callback(file_path)
                        except Exception as e:
                            # Don't let one bad callback break the others
                            print(f"Error in file watcher callback: {e}")
                            
            except Exception as e:
                print(f"Error checking file {file_path}: {e}")
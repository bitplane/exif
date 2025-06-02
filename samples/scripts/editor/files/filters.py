"""
Base filter classes for file filtering system
"""

import re
import abc
from typing import List, Dict, Any, Optional, Type


class Filter(abc.ABC):
    """Abstract base class for filters"""
    
    # Override in subclasses to define parameters for modal introspection
    # Format: [(param_name, param_type, description), ...]
    PARAMETERS = []
    
    @abc.abstractmethod
    def apply(self, path: str) -> str:
        """Apply filter to a path. 
        Returns modified path or raises StopIteration to filter out.
        """
        pass
    
    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        pass
    
    @classmethod
    @abc.abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Filter':
        """Create from dict"""
        pass
    
    def __str__(self) -> str:
        """String representation for UI display"""
        return f"{self.__class__.__name__}"


class IgnoreFilter(Filter):
    """Filter that ignores files matching a pattern"""
    
    PARAMETERS = [("pattern", str, "Regex pattern to match")]
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        try:
            self._compiled = re.compile(pattern)
        except re.error:
            # Store invalid pattern but mark as invalid
            self._compiled = None
    
    def apply(self, path: str) -> str:
        if self._compiled and self._compiled.search(path):
            raise StopIteration()
        return path
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ignore",
            "pattern": self.pattern
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IgnoreFilter':
        return cls(data["pattern"])
    
    def __str__(self) -> str:
        return self.pattern


class EditFilter(Filter):
    """Filter that edits/replaces text in paths"""
    
    PARAMETERS = [
        ("find", str, "Pattern to find"),
        ("replacement", str, "Replacement text")
    ]
    
    def __init__(self, find: str, replacement: str):
        self.find = find
        self.replacement = replacement
        try:
            self._compiled = re.compile(find)
        except re.error:
            self._compiled = None
    
    def apply(self, path: str) -> str:
        if self._compiled:
            return self._compiled.sub(self.replacement, path)
        return path
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "edit",
            "find": self.find,
            "replacement": self.replacement
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditFilter':
        return cls(data["find"], data["replacement"])
    
    def __str__(self) -> str:
        return f"{self.find} → {self.replacement}"


class FiltersChain(Filter):
    """Filter that chains multiple filters together"""
    
    # No parameters - this is constructed programmatically
    PARAMETERS = []
    
    def __init__(self, *filters: Filter):
        self.filters = list(filters)
    
    def apply(self, path: str) -> str:
        current = path
        for filter_obj in self.filters:
            current = filter_obj.apply(current)
        return current
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "chain",
            "filters": [f.to_dict() for f in self.filters]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FiltersChain':
        filters = [load_filter(f) for f in data["filters"]]
        return cls(*filters)
    
    def __str__(self) -> str:
        return f"Chain: {len(self.filters)} filters"


# Filter type registry
FILTER_TYPES: Dict[str, Type[Filter]] = {
    "ignore": IgnoreFilter,
    "edit": EditFilter,
    "chain": FiltersChain
}


def create_filter(filter_type: str, *args) -> Filter:
    """Create a filter by type name with arguments"""
    if filter_type not in FILTER_TYPES:
        raise ValueError(f"Unknown filter type: {filter_type}")
    
    filter_class = FILTER_TYPES[filter_type]
    return filter_class(*args)


def load_filter(data: Dict[str, Any]) -> Filter:
    """Load a filter from dict data"""
    filter_type = data.get("type")
    if filter_type not in FILTER_TYPES:
        raise ValueError(f"Unknown filter type: {filter_type}")
    
    filter_class = FILTER_TYPES[filter_type]
    return filter_class.from_dict(data)


def load_filters_from_json(data: Dict[str, Any]) -> List[Filter]:
    """Load filters from the JSON format used in filters.json"""
    filters = []
    
    files_data = data.get("files", {})
    
    # Load ignore patterns
    for pattern in files_data.get("ignore", []):
        filters.append(IgnoreFilter(pattern))
    
    # Load edit patterns
    for find, replacement in files_data.get("edit", []):
        filters.append(EditFilter(find, replacement))
    
    return filters


def save_filters_to_json(filters: List[Filter]) -> Dict[str, Any]:
    """Save filters to the JSON format used in filters.json"""
    ignore_patterns = []
    edit_patterns = []
    
    for filter_obj in filters:
        if isinstance(filter_obj, IgnoreFilter):
            ignore_patterns.append(filter_obj.pattern)
        elif isinstance(filter_obj, EditFilter):
            edit_patterns.append([filter_obj.find, filter_obj.replacement])
        # Skip chains for now - they're not in the current format
    
    return {
        "files": {
            "ignore": ignore_patterns,
            "edit": edit_patterns
        }
    }


# Shorter aliases
load = load_filters_from_json
save = save_filters_to_json

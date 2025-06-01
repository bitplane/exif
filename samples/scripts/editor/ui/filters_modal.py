"""
Dynamic filter selection and editing using OptionList
"""

from typing import Dict, Any
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option
from textual.containers import Container, Vertical
from textual import on

from files.filters import FILTER_TYPES


class FilterModal(ModalScreen):
    """Compact modal for editing filter parameters"""
    
    CSS = """
    FilterModal {
        align: center middle;
    }
    
    FilterModal Container {
        background: $surface;
        border: solid $primary;
        width: 40;
        height: auto;
        padding: 1;
    }
    
    FilterModal Input {
        width: 100%;
        margin-top: 1;
    }
    """
    
    def __init__(self, filter_type: str, title: str = "Add Filter", 
                 initial_values: Dict[str, Any] = None):
        super().__init__()
        self.filter_type = filter_type
        self.title = title
        self.filter_class = FILTER_TYPES.get(filter_type)
        self.initial_values = initial_values or {}
        self.inputs = {}
        
        if not self.filter_class:
            raise ValueError(f"Unknown filter type: {filter_type}")
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title)
            
            # Get filter class parameters
            params = self.filter_class.PARAMETERS
            
            # Create input fields
            for param_name, param_type, description in params:
                yield Label(f"{param_name}:")
                
                initial = self.initial_values.get(param_name, "")
                
                input_widget = Input(
                    value=str(initial),
                    placeholder=description or f"Enter {param_name}"
                )
                self.inputs[param_name] = input_widget
                yield input_widget
    
    @on(Input.Submitted)
    def submit_form(self, event: Input.Submitted) -> None:
        """Submit when Enter pressed"""
        # Collect values
        values = {}
        for param_name, input_widget in self.inputs.items():
            values[param_name] = input_widget.value
        
        # Validate required fields
        for param_name in self.inputs:
            if not values.get(param_name):
                self.notify(f"{param_name} is required", severity="error")
                return
        
        self.dismiss(values)
    
    def on_key(self, event) -> None:
        """Handle escape key"""
        if event.key == "escape":
            self.dismiss(None)


class FilterListModal(ModalScreen):
    """Compact popup menu for filter type selection"""
    
    CSS = """
    FilterListModal {
        align: center middle;
    }
    
    FilterListModal Container {
        background: $surface;
        width: 25;
        height: auto;
        padding: 0;
    }
    
    FilterListModal OptionList {
        width: 100%;
        height: auto;
        min-height: 3;
        max-height: 10;
        background: $surface;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container():
            # Build options from FILTER_TYPES dynamically
            options = []
            for filter_name, filter_class in sorted(FILTER_TYPES.items()):
                if hasattr(filter_class, 'PARAMETERS') and filter_class.PARAMETERS:
                    options.append(Option(filter_name.title(), id=filter_name))
            
            yield OptionList(*options, id="filter_list")
    
    @on(OptionList.OptionSelected)
    def option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle filter type selection"""
        self.dismiss(event.option.id)
    
    def on_key(self, event) -> None:
        """Handle escape key"""
        if event.key == "escape":
            self.dismiss(None)
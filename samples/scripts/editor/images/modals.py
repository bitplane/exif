"""
Modal dialogs for filter editing
"""

from textual.screen import ModalScreen
from textual.widgets import Label, Input
from textual.containers import Container
from textual import events


class IgnoreFilterModal(ModalScreen):
    """Modal dialog for editing ignore filter patterns"""

    CSS = """
    IgnoreFilterModal {
        align: center middle;
    }
    
    IgnoreFilterModal > Container {
        width: 60;
        height: 11;
        border: thick $background;
        background: $surface;
    }
    
    IgnoreFilterModal Label {
        margin: 1 2;
    }
    
    IgnoreFilterModal Input {
        margin: 0 2 1 2;
    }
    """

    def __init__(self, initial_value: str = "", title: str = "Add Ignore Filter"):
        super().__init__()
        self.initial_value = initial_value
        self.title = title

    def compose(self):
        with Container():
            yield Label(self.title)
            yield Input(value=self.initial_value, placeholder="Enter regex pattern...")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.prevent_default()


class ReplaceFilterModal(ModalScreen):
    """Modal dialog for editing replace filter patterns"""

    CSS = """
    ReplaceFilterModal {
        align: center middle;
    }
    
    ReplaceFilterModal > Container {
        width: 70;
        height: 15;
        border: thick $background;
        background: $surface;
    }
    
    ReplaceFilterModal Label {
        margin: 1 2;
    }
    
    ReplaceFilterModal Input {
        margin: 0 2 1 2;
    }
    """

    def __init__(self, find_pattern: str = "", replace_pattern: str = ""):
        super().__init__()
        self.find_pattern = find_pattern
        self.replace_pattern = replace_pattern

    def compose(self):
        with Container():
            yield Label("Replace Pattern")
            yield Input(value=self.find_pattern, placeholder="Find regex pattern...", id="find_input")
            yield Label("Replace With")
            yield Input(value=self.replace_pattern, placeholder="Replacement text...", id="replace_input")

    def on_mount(self) -> None:
        self.query_one("#find_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "find_input":
            # Move to replace input
            self.query_one("#replace_input", Input).focus()
        else:
            # Submit the form
            find_val = self.query_one("#find_input", Input).value
            replace_val = self.query_one("#replace_input", Input).value
            self.dismiss((find_val, replace_val))
    
    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.prevent_default()
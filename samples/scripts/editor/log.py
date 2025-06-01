"""
Log display widget
"""

from datetime import datetime
from textual.widgets import RichLog
from textual.containers import Container


class LogWidget(Container):
    """Container for the log display"""
    
    def compose(self):
        yield RichLog(highlight=True, markup=True, id="log_widget")
    
    def write_log(self, message: str, level: str = "info") -> None:
        """Log a message to the log widget"""
        log_widget = self.query_one("#log_widget", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "error":
            log_widget.write(
                f"[red]{timestamp}[/red] [bold red]ERROR[/bold red] {message}"
            )
        elif level == "warning":
            log_widget.write(
                f"[yellow]{timestamp}[/yellow] [bold yellow]WARN[/bold yellow] {message}"
            )
        elif level == "debug":
            log_widget.write(f"[dim]{timestamp} DEBUG {message}[/dim]")
        else:
            log_widget.write(
                f"[green]{timestamp}[/green] [bold green]INFO[/bold green] {message}"
            )
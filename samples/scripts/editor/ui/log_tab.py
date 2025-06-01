"""
Log display widget with Python logging integration
"""

import logging
from datetime import datetime
from textual.widgets import RichLog
from textual.containers import Container


class TextualLogHandler(logging.Handler):
    """Logging handler that writes to a Textual RichLog widget"""
    
    def __init__(self, log_widget=None):
        super().__init__()
        self.log_widget = log_widget
        self.pending_records = []
        
    def set_widget(self, log_widget):
        """Set the log widget and flush any pending records"""
        self.log_widget = log_widget
        # Flush any pending log records
        for record in self.pending_records:
            self._write_record(record)
        self.pending_records.clear()
    
    def emit(self, record):
        """Emit a log record"""
        if self.log_widget is None:
            # Store for later if widget not ready yet
            self.pending_records.append(record)
            return
            
        self._write_record(record)
    
    def _write_record(self, record):
        """Write a log record to the widget"""
        try:
            # Format the message
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            
            # Get the RichLog widget from the container
            rich_log = self.log_widget.query_one("#log_widget", RichLog)
            
            # Write with appropriate styling based on level
            if record.levelno >= logging.ERROR:
                rich_log.write(
                    f"[red]{timestamp}[/red] [bold red]{record.levelname}[/bold red] {msg}"
                )
            elif record.levelno >= logging.WARNING:
                rich_log.write(
                    f"[yellow]{timestamp}[/yellow] [bold yellow]{record.levelname}[/bold yellow] {msg}"
                )
            elif record.levelno <= logging.DEBUG:
                rich_log.write(f"[dim]{timestamp} {record.levelname} {msg}[/dim]")
            else:  # INFO
                rich_log.write(
                    f"[green]{timestamp}[/green] [bold green]{record.levelname}[/bold green] {msg}"
                )
        except Exception:
            # Silently ignore logging errors to avoid recursion
            pass


class LogWidget(Container):
    """Container for the log display"""
    
    def compose(self):
        yield RichLog(highlight=True, markup=True, id="log_widget")
    
    def write_log(self, message: str, level: str = "info") -> None:
        """Legacy method - use logging module instead"""
        logger = logging.getLogger("editor")
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "debug":
            logger.debug(message)
        else:
            logger.info(message)


def setup_logging(log_widget=None, level=logging.DEBUG):
    """Setup logging with the textual handler"""
    # Get the root logger for the editor package
    logger = logging.getLogger("editor")
    logger.setLevel(level)
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Create and add our custom handler
    handler = TextualLogHandler(log_widget)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    # Also capture warnings
    logging.captureWarnings(True)
    
    return logger, handler
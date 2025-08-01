"""Export engine for query results in multiple formats."""

try:
    # Try the full streaming exporter first
    from .streaming_exporter import StreamingExporter, ExportFormat
    HAS_STREAMING = True
except ImportError:
    # Fall back to simple exporter
    from .simple_exporter import StreamingExporter, ExportFormat
    HAS_STREAMING = False

from .export_manager import ExportManager, ExportJob

__all__ = [
    'StreamingExporter',
    'ExportFormat',
    'ExportManager',
    'ExportJob'
]
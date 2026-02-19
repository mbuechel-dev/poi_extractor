"""POI Extractor - Extract POIs along routes and export to Garmin."""

__version__ = "0.1.0"

# Expose main classes for programmatic use
from .core import Config
from .extractors import get_extractor, SimpleExtractor, StagesExtractor
from .exporters import GarminExporter

__all__ = [
    "__version__",
    "Config",
    "get_extractor",
    "SimpleExtractor",
    "StagesExtractor",
    "GarminExporter",
]

# LocalExtractor is only available if optional dependencies are installed
try:
    from .extractors import LocalExtractor
    __all__.append("LocalExtractor")
except ImportError:
    pass

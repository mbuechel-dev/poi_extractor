"""POI extraction strategies."""

from .simple import SimpleExtractor
from .stages import StagesExtractor

# Try to import local extractor (requires optional dependencies)
try:
    from .local import LocalExtractor
    LOCAL_AVAILABLE = True
except ImportError:
    LOCAL_AVAILABLE = False
    LocalExtractor = None


def get_extractor(strategy="simple"):
    """
    Factory function to get the appropriate extractor.
    
    Args:
        strategy: One of 'simple', 'stages', or 'local'
        
    Returns:
        Extractor class
        
    Raises:
        ValueError: If strategy is invalid
        ImportError: If strategy requires unavailable dependencies
    """
    if strategy == "simple":
        return SimpleExtractor
    elif strategy == "stages":
        return StagesExtractor
    elif strategy == "local":
        if not LOCAL_AVAILABLE:
            raise ImportError(
                "Local extractor requires optional dependencies. "
                "Install with: pip install poi-extractor[local]"
            )
        return LocalExtractor
    else:
        raise ValueError(
            f"Unknown strategy: {strategy}. "
            f"Valid options: simple, stages, local"
        )


__all__ = ["get_extractor", "SimpleExtractor", "StagesExtractor"]
if LOCAL_AVAILABLE:
    __all__.append("LocalExtractor")

class ExtractionError(Exception):
    """Raise when extract stage fails."""
    pass

class TransformationError(Exception):
    """Raise when transform stage fails."""
    pass

class LoadError(Exception):
    """Raise when Load stage fails."""
    pass
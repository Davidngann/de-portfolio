class ExtractionError(Exception):
    """Raised when the source file cannot be read or fails schema validation."""
    pass

class TransformationError(Exception):
    """Raise when a transformation step produces an invalid or empty result."""
    pass

class LoadError(Exception):
    """Raise when the database connection fails or an insert cannot completed."""
    pass
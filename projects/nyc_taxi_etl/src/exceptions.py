class ExtractionError(Exception):
    """
    Raised when the source file cannot be read,
    is missing expected columns, or returns zero rows.
    """
    pass

class TransformationError(Exception):
    """
    Raise when a transformation step produces
    an invalid or empty result.
    """
    pass

class LoadError(Exception):
    """
    Raise when the database connection fails 
    or a batch insert cannot completed.
    """
    pass
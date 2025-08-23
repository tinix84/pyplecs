"""PyPLECS exception classes.

This module defines the project's custom exception hierarchy.
"""


class PyPlecsError(Exception):
    """Base exception for PyPLECS."""
    pass

class PlecsConnectionError(PyPlecsError):
    """Raised for PLECS server connection issues."""
    pass

class SimulationError(PyPlecsError):
    """Raised for simulation execution errors."""
    pass

class ModelParsingError(PyPlecsError):
    """Raised for model file parsing errors."""
    pass

class FileLoadError(PyPlecsError):
    """Raised for file loading errors."""
    pass

class ConfigurationError(PyPlecsError):
    """Raised for configuration and setup errors."""
    pass

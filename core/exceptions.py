class AppError(Exception):
    """Base exception class for all application errors."""
    def __init__(self, msg: str, code: int = 0):
        super().__init__(msg)
        self.code = code

class ConfigError(AppError): pass
class StorageError(AppError): pass
class ValidationError(AppError): pass
class IntegrityError(AppError): pass
class DuplicateSignalError(AppError): pass
class StateError(AppError): pass

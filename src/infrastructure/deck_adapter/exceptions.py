class DeckAdapterError(Exception):
    """Base exception for deck adapter errors."""


class DeckEmptyError(DeckAdapterError):
    """Raised when drawing from an empty deck."""


class InvalidDrawCountError(DeckAdapterError):
    """Raised when draw_many receives an invalid count."""


class DuplicateTokenIdError(DeckAdapterError):
    """Raised when input token IDs contain duplicates."""

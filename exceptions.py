"""Our own error types. Clients and services raise them; main.py turns them into HTTP responses."""


class NotFoundError(Exception):
    """Something we looked for does not exist."""


class CountryNotFoundError(NotFoundError):
    """The country does not exist."""


class TripNotFoundError(NotFoundError):
    """The trip does not exist."""


class UpstreamError(Exception):
    """An outside API is down, too slow, or returned something unusable."""